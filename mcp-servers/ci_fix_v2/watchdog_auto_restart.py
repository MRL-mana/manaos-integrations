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
import os
import atexit
from pathlib import Path
import requests
import schedule


def _resolve_port(service_name: str, default: int, category: str) -> int:
    env_map = {
        "unified_api": "UNIFIED_API_PORT",
        "mrl_memory": "MRL_MEMORY_PORT",
    }
    env_key = env_map.get(service_name)
    if env_key:
        env_value = os.getenv(env_key)
        if env_value:
            try:
                return int(env_value)
            except ValueError:
                pass

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from config_loader import get_port

        return int(get_port(service_name, category))
    except Exception:
        return default


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_singleton_lock(lock_file: Path) -> bool:
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(str(os.getpid()))
            break
        except FileExistsError:
            try:
                existing_pid = int(lock_file.read_text(encoding='utf-8').strip() or '0')
            except Exception:
                existing_pid = 0

            if _is_pid_alive(existing_pid):
                print(f"[SKIP] watchdog already running (PID: {existing_pid})")
                return False

            try:
                lock_file.unlink()
            except OSError:
                time.sleep(0.1)

    def _cleanup_lock() -> None:
        try:
            if lock_file.exists():
                pid_text = lock_file.read_text(encoding='utf-8').strip()
                if pid_text == str(os.getpid()):
                    lock_file.unlink()
        except OSError:
            pass

    atexit.register(_cleanup_lock)
    return True


class ServiceWatchdog:
    """サービス監視と自動再起動"""
    
    def __init__(self, check_interval=60):
        """
        初期化
        
        Args:
            check_interval: チェック間隔（秒）
        """
        self.check_interval = check_interval
        self.repo_root = Path(__file__).resolve().parents[1]
        self.python_cmd = sys.executable or "python"

        mrl_memory_port = _resolve_port("mrl_memory", 5105, "manaos_services")
        unified_api_port = _resolve_port("unified_api", 9502, "integration_services")

        self.services = {
            'MRL Memory': {
                'url': f'http://localhost:{mrl_memory_port}/health',
                'port': mrl_memory_port,
                'startup_cmd': [self.python_cmd, str(self.repo_root / 'mrl_memory_integration.py')],
            },
            'Unified API': {
                'url': f'http://localhost:{unified_api_port}/health',
                'port': unified_api_port,
                'startup_cmd': [self.python_cmd, str(self.repo_root / 'unified_api' / 'unified_api_server.py')],
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
    repo_root = Path(__file__).resolve().parents[1]
    lock_file = repo_root / 'logs' / 'watchdog.pid'
    if not _acquire_singleton_lock(lock_file):
        return

    watchdog = ServiceWatchdog(check_interval=60)
    
    # システム起動時チェック
    watchdog.startup_check()
    
    # 監視ループ開始
    watchdog.monitor_loop()


if __name__ == '__main__':
    main()
