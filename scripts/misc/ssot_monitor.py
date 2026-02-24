#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 ManaOS SSOT Generator監視システム
SSOT Generatorの監視と自動再起動
"""

import os
import json
import logging
import httpx
import psutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from manaos_error_handler import ManaOSErrorHandler
from manaos_logger import get_logger
from manaos_process_manager import ProcessManager

logger = get_logger("SSOTMonitor")
error_handler = ManaOSErrorHandler("SSOT Monitor")
process_manager = ProcessManager("SSOT Monitor")

# SSOT Generator設定
SSOT_GENERATOR_SCRIPT = "ssot_generator.py"
SSOT_GENERATOR_PORT = 0  # SSOT Generatorはポートを持たない
SSOT_FILE = Path(__file__).parent / "manaos_status.json"
CHECK_INTERVAL = 10  # 監視間隔（秒）
MAX_RESTARTS = 5  # 最大再起動回数
RESTART_DELAY = 5  # 再起動待機時間（秒）


class SSOTMonitor:
    """SSOT Generator監視クラス"""
    
    def __init__(self):
        """初期化"""
        self.restart_count = 0
        self.last_restart_time = None
        self.process_pid = None
        self.monitoring = False
    
    def check_ssot_generator_running(self) -> bool:
        """SSOT Generatorが実行中か確認"""
        try:
            process_info = process_manager.get_process_info(SSOT_GENERATOR_SCRIPT)
            if process_info:
                self.process_pid = process_info["pid"]
                return True
            return False
        except Exception as e:
            logger.error(f"プロセス確認エラー: {e}")
            return False
    
    def check_ssot_file_fresh(self) -> bool:
        """SSOTファイルが新鮮か確認（5秒以内に更新されているか）"""
        try:
            if not SSOT_FILE.exists():
                return False
            
            file_mtime = SSOT_FILE.stat().st_mtime
            age_seconds = time.time() - file_mtime
            
            # 5秒以内に更新されていれば新鮮
            return age_seconds < 5
        except Exception as e:
            logger.error(f"SSOTファイル確認エラー: {e}")
            return False
    
    def start_ssot_generator(self) -> bool:
        """SSOT Generatorを起動"""
        try:
            script_path = Path(__file__).parent / SSOT_GENERATOR_SCRIPT
            
            if not script_path.exists():
                logger.error(f"SSOT Generatorスクリプトが見つかりません: {script_path}")
                return False
            
            # プロセス起動
            process = subprocess.Popen(
                ["python", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(script_path.parent)
            )
            
            self.process_pid = process.pid
            process_manager.save_process_info(SSOT_GENERATOR_SCRIPT, process.pid)
            
            logger.info(f"SSOT Generator起動: PID {process.pid}")
            
            # 起動確認（少し待つ）
            time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"SSOT Generator起動エラー: {e}")
            error_handler.handle_exception(e, context={"action": "start_ssot_generator"})
            return False
    
    def restart_ssot_generator(self) -> bool:
        """SSOT Generatorを再起動"""
        # 再起動回数チェック
        if self.restart_count >= MAX_RESTARTS:
            logger.error(f"最大再起動回数に達しました: {MAX_RESTARTS}")
            return False
        
        # 再起動間隔チェック
        if self.last_restart_time:
            time_since_last_restart = (datetime.now() - self.last_restart_time).total_seconds()
            if time_since_last_restart < RESTART_DELAY:
                logger.warning(f"再起動間隔が短すぎます。待機中...")
                time.sleep(RESTART_DELAY - time_since_last_restart)
        
        logger.warning(f"SSOT Generator再起動中... ({self.restart_count + 1}/{MAX_RESTARTS})")
        
        # 既存プロセスを停止
        if self.process_pid:
            try:
                process_manager.cleanup_process(SSOT_GENERATOR_SCRIPT)
            except Exception as e:
                logger.warning(f"プロセス停止エラー（無視）: {e}")
        
        # 再起動
        success = self.start_ssot_generator()
        
        if success:
            self.restart_count += 1
            self.last_restart_time = datetime.now()
        
        return success
    
    def monitor_loop(self):
        """監視ループ"""
        logger.info(f"🔍 SSOT Generator監視開始 (間隔: {CHECK_INTERVAL}秒)")
        self.monitoring = True
        
        while self.monitoring:
            try:
                # SSOT Generatorが実行中か確認
                is_running = self.check_ssot_generator_running()
                
                # SSOTファイルが新鮮か確認
                is_fresh = self.check_ssot_file_fresh()
                
                if not is_running:
                    logger.warning("SSOT Generatorが実行されていません。起動します...")
                    self.start_ssot_generator()
                elif not is_fresh:
                    logger.warning("SSOTファイルが更新されていません。再起動します...")
                    self.restart_ssot_generator()
                else:
                    # 正常動作中
                    logger.debug("SSOT Generator正常動作中")
                    self.restart_count = 0  # 正常動作が続けば再起動カウントをリセット
                
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("監視を停止します...")
                self.monitoring = False
                break
            except Exception as e:
                logger.error(f"監視ループエラー: {e}")
                error_handler.handle_exception(e, context={"action": "monitor_loop"})
                time.sleep(CHECK_INTERVAL)
    
    def stop(self):
        """監視を停止"""
        self.monitoring = False
        logger.info("SSOT Generator監視を停止しました")


def main():
    """メイン関数"""
    monitor = SSOTMonitor()
    
    # 初回起動確認
    if not monitor.check_ssot_generator_running():
        logger.info("SSOT Generatorが起動していません。起動します...")
        monitor.start_ssot_generator()
    
    # 監視ループ開始
    try:
        monitor.monitor_loop()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == '__main__':
    main()

