#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高度な自動化システム - 完全統合版
Obsidian-Notionミラーリング + Gemini API + 音声制御 + ダッシュボード統合
"""

import os
import sys
import time
import json
import yaml
import logging
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import sqlite3
import queue
import signal

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedAutomationSystem:
    """高度な自動化システム - 完全統合版"""
    
    def __init__(self):
        self.config = self.load_config()
        self.running = True
        self.processes = {}
        self.message_queue = queue.Queue()
        self.setup_signal_handlers()
        
    def load_config(self) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        try:
            with open('mirror_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info("設定ファイル読み込み完了")
            return config
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return {}
    
    def setup_signal_handlers(self):
        """シグナルハンドラー設定"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """シグナル処理"""
        logger.info(f"シグナル {signum} を受信しました。システムを停止します。")
        self.running = False
        self.stop_all_processes()
        sys.exit(0)
    
    def start_obsidian_notion_mirror(self):
        """Obsidian-Notionミラーリングシステム開始"""
        try:
            cmd = ["python3", "obsidian_notion_mirror_system.py"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['obsidian_notion_mirror'] = process
            logger.info("Obsidian-Notionミラーリングシステム開始")
            return True
        except Exception as e:
            logger.error(f"Obsidian-Notionミラーリング開始エラー: {e}")
            return False
    
    def start_gemini_api_system(self):
        """Gemini APIシステム開始"""
        try:
            cmd = ["python3", "gemini_api_fix.py"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['gemini_api'] = process
            logger.info("Gemini APIシステム開始")
            return True
        except Exception as e:
            logger.error(f"Gemini APIシステム開始エラー: {e}")
            return False
    
    def start_dashboard(self):
        """統合ダッシュボード開始"""
        try:
            cmd = ["python3", "ultimate_integration_dashboard_fixed.py"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['dashboard'] = process
            logger.info("統合ダッシュボード開始")
            return True
        except Exception as e:
            logger.error(f"ダッシュボード開始エラー: {e}")
            return False
    
    def monitor_processes(self):
        """プロセス監視"""
        while self.running:
            for name, process in self.processes.items():
                if process.poll() is not None:
                    logger.warning(f"{name}プロセスが停止しました。再起動します。")
                    self.restart_process(name)
            time.sleep(30)
    
    def restart_process(self, process_name: str):
        """プロセス再起動"""
        if process_name == 'obsidian_notion_mirror':
            self.start_obsidian_notion_mirror()
        elif process_name == 'gemini_api':
            self.start_gemini_api_system()
        elif process_name == 'dashboard':
            self.start_dashboard()
    
    def stop_all_processes(self):
        """全プロセス停止"""
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"{name}プロセス停止完了")
            except Exception as e:
                logger.error(f"{name}プロセス停止エラー: {e}")
                process.kill()
    
    def system_health_check(self):
        """システム健全性チェック"""
        health_status = {
            'obsidian_notion_mirror': False,
            'gemini_api': False,
            'dashboard': False,
            'database': False,
            'config': False
        }
        
        # プロセスチェック
        for name, process in self.processes.items():
            if process.poll() is None:
                health_status[name] = True
        
        # データベースチェック
        try:
            conn = sqlite3.connect('obsidian_notion_mirror.db')
            conn.close()
            health_status['database'] = True
        except Exception:
            pass
        
        # 設定チェック
        if self.config:
            health_status['config'] = True
        
        return health_status
    
    def generate_status_report(self):
        """ステータスレポート生成"""
        health = self.system_health_check()
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': 'running' if self.running else 'stopped',
            'health_status': health,
            'active_processes': len([p for p in self.processes.values() if p.poll() is None]),
            'total_processes': len(self.processes)
        }
        
        with open('system_status_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("ステータスレポート生成完了")
        return report
    
    def run(self):
        """メイン実行"""
        logger.info("高度な自動化システム開始")
        
        # 各システム開始
        self.start_obsidian_notion_mirror()
        self.start_gemini_api_system()
        self.start_dashboard()
        
        # 監視スレッド開始
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        # メインループ
        while self.running:
            try:
                # ステータスレポート生成（1時間ごと）
                if datetime.now().minute == 0:
                    self.generate_status_report()
                
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("キーボード割り込みを受信しました")
                break
            except Exception as e:
                logger.error(f"メインループエラー: {e}")
                time.sleep(10)
        
        self.stop_all_processes()
        logger.info("高度な自動化システム停止")

def main():
    """メイン関数"""
    system = AdvancedAutomationSystem()
    system.run()

if __name__ == "__main__":
    main() 