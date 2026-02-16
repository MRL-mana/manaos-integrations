#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 統合システム 自動再起動ウォッチドッグ

システム起動時または定期的にサービスの稼働状況を監視し、
ダウンしていたら自動的に再起動する

本番運用用の信頼性向上スクリプト
"""

import subprocess
import sys
import time
import logging
from pathlib import Path
import requests
import schedule


class ServiceWatchdog:
    """サービス監視と自動再起動"""
    
    def __init__(self, check_interval=60):
        """
        初期化
        
        Args:
            check_interval: チェック間隔（秒）
        """
        self.check_interval = check_interval
        self.services = {
            'MRL Memory': {
                'url': 'http://localhost:5110/health',
                'port': 5110,
                'startup_cmd': ['python', '-m', 'mrl_memory_integration'],
            },
            'Unified API': {
                'url': 'http://localhost:9502/health',
                'port': 9502,
                'startup_cmd': ['python', 'unified_api_server.py'],
            },
        }
        
        # ログ設定
        self.setup_logging()
    
    def setup_logging(self):
        """ログシステムの設定"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'watchdog.log'),
                logging.StreamHandler(),
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def check_service(self, service_name, service_config) -> bool:
        """
        サービスのヘルスチェック
        
        Args:
            service_name: サービス名
            service_config: サービス設定
        
        Returns:
            True: サービスが稼働中
            False: サービスが停止中
        """
        try:
            response = requests.get(
                service_config['url'],
                timeout=5
            )
            
            if response.status_code == 200:
                self.logger.info(f'[OK] {service_name}: 稼働中')
                return True
            else:
                self.logger.warning(f'[!] {service_name}: ステータスコード {response.status_code}')
                return False
        
        except requests.exceptions.ConnectionError:
            self.logger.warning(f'[NG] {service_name}: 接続失敗')
            return False
        except requests.exceptions.Timeout:
            self.logger.warning(f'[NG] {service_name}: タイムアウト')
            return False
        except Exception as e:
            self.logger.error(f'[NG] {service_name}: {str(e)[:60]}')
            return False
    
    def restart_service(self, service_name, service_config):
        """
        サービスの再起動
        
        Args:
            service_name: サービス名
            service_config: サービス設定
        """
        self.logger.warning(f'[RESTART] {service_name} を再起動します...')
        
        try:
            # サービス起動
            subprocess.Popen(
                service_config['startup_cmd'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # 起動待機
            time.sleep(5)
            
            # 再確認
            if self.check_service(service_name, service_config):
                self.logger.info(f'[OK] {service_name}: 再起動完了')
            else:
                self.logger.error(f'[NG] {service_name}: 再起動失敗')
        
        except Exception as e:
            self.logger.error(f'[NG] {service_name} 再起動エラー: {str(e)[:60]}')
    
    def monitor_loop(self):
        """監視ループ"""
        self.logger.info('=' * 70)
        self.logger.info('ManaOS Watchdog: 監視開始')
        self.logger.info('=' * 70)
        
        schedule.every(self.check_interval).seconds.do(self.health_check)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('監視終了')
    
    def health_check(self):
        """全サービスのヘルスチェック"""
        self.logger.info('-' * 70)
        
        for service_name, service_config in self.services.items():
            is_healthy = self.check_service(service_name, service_config)
            
            if not is_healthy:
                self.restart_service(service_name, service_config)
        
        self.logger.info('-' * 70)
    
    def startup_check(self):
        """システム起動時チェック"""
        self.logger.info('=' * 70)
        self.logger.info('システム起動時チェック')
        self.logger.info('=' * 70)
        
        # 全サービスをチェック
        all_good = True
        for service_name, service_config in self.services.items():
            is_healthy = self.check_service(service_name, service_config)
            if not is_healthy:
                all_good = False
                self.restart_service(service_name, service_config)
        
        if all_good:
            self.logger.info('[OK] 全サービスが正常に稼働しています')
        else:
            self.logger.warning('[!] 一部サービスを再起動しました')
        
        return all_good


def main():
    """メイン関数"""
    watchdog = ServiceWatchdog(check_interval=60)
    
    # システム起動時チェック
    watchdog.startup_check()
    
    # 監視ループ開始
    watchdog.monitor_loop()


if __name__ == '__main__':
    main()
