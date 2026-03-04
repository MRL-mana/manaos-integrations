#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ManaOS ログ監視・アラートシステム
リアルタイムで logs/ ディレクトリを監視し、エラーを検出してアラートを発行
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from threading import Thread
import re

# 設定
CONFIG = {
    "log_dir": Path("logs"),
    "watch_files": [
        "watchdog.log",
        "unified_api.log",
        "mrl_memory.log",
    ],
    "alert_keywords": {
        "CRITICAL": r"(CRITICAL|ERROR|FATAL|EXCEPTION|CRASH)",
        "WARNING": r"(WARNING|WARN|DEPRECATED|TIMEOUT)",
        "SERVICE_DOWN": r"(Connection refused|Service unavailable|Failed to connect)",
    },
    "check_interval": 10,  # 秒
    "alert_history_file": "logs/alert_history.json",
}

class LogWatcher:
    """ログファイル監視クラス"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.file_positions = {}
        self.alert_history = self._load_alert_history()
        self.running = True
        
    def _setup_logger(self):
        """ロギング設定"""
        logger = logging.getLogger("LogWatcher")
        logger.setLevel(logging.INFO)
        
        # ファイルハンドラ
        log_file = CONFIG["log_dir"] / "log_watcher.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        # フォーマッタ
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        return logger
    
    def _load_alert_history(self):
        """アラート履歴の読み込み"""
        history_file = Path(CONFIG["alert_history_file"])
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_alert_history(self):
        """アラート履歴の保存"""
        history_file = Path(CONFIG["alert_history_file"])
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.alert_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"アラート履歴保存エラー: {e}")
    
    def _check_log_file(self, log_file_path):
        """ログファイルの新規行をチェック"""
        if not log_file_path.exists():
            return []
        
        # ファイルサイズから読み出し位置を取得
        file_size = log_file_path.stat().st_size
        last_pos = self.file_positions.get(str(log_file_path), 0)
        
        # ファイルがリセットされた場合
        if file_size < last_pos:
            last_pos = 0
        
        # 新規行を読み込み
        new_lines = []
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                self.file_positions[str(log_file_path)] = f.tell()
        except Exception as e:
            self.logger.warning(f"ログ読み込みエラー ({log_file_path}): {e}")
        
        return new_lines
    
    def _detect_alerts(self, log_file_name, lines):
        """ログ行からアラートを検出"""
        alerts = []
        
        for severity, pattern in CONFIG["alert_keywords"].items():
            for line in lines:
                if re.search(pattern, line, re.IGNORECASE):
                    alert = {
                        "timestamp": datetime.now().isoformat(),
                        "severity": severity,
                        "source_file": log_file_name,
                        "message": line.strip(),
                    }
                    alerts.append(alert)
        
        return alerts
    
    def _issue_alert(self, alert):
        """アラートを発行"""
        severity = alert["severity"]
        source = alert["source_file"]
        message = alert["message"][:100]
        
        # ログに記録
        level_map = {
            "CRITICAL": logging.CRITICAL,
            "WARNING": logging.WARNING,
            "SERVICE_DOWN": logging.CRITICAL,
        }
        log_level = level_map.get(severity, logging.WARNING)
        self.logger.log(log_level, f"[{source}] {severity}: {message}")
        
        # アラート履歴に追加
        alert_key = f"{source}_{severity}_{message[:50]}"
        if alert_key not in self.alert_history:
            self.alert_history[alert_key] = {
                "first_time": alert["timestamp"],
                "count": 0,
            }
        self.alert_history[alert_key]["count"] += 1
        self.alert_history[alert_key]["last_time"] = alert["timestamp"]
        
        # 重大度に応じた処理
        if severity == "CRITICAL" or severity == "SERVICE_DOWN":
            self._handle_critical_alert(alert)
    
    def _handle_critical_alert(self, alert):
        """重大アラートの処理"""
        msg = f"\n{'='*60}\n"
        msg += f"[CRITICAL] ManaOS アラート通知\n"
        msg += f"{'='*60}\n"
        msg += f"時刻: {alert['timestamp']}\n"
        msg += f"レベル: {alert['severity']}\n"
        msg += f"ソース: {alert['source_file']}\n"
        msg += f"メッセージ: {alert['message']}\n"
        msg += f"{'='*60}\n"
        
        # コンソール出力
        print(msg)
        
        # 通知ファイルに記録
        alert_file = CONFIG["log_dir"] / "critical_alerts.txt"
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(msg)
    
    def watch_logs(self):
        """ログを監視（メインループ）"""
        self.logger.info("ログ監視を開始しました")
        print("[OK] ログ監視システムが起動しました")
        
        while self.running:
            try:
                for log_file_name in CONFIG["watch_files"]:
                    log_file_path = CONFIG["log_dir"] / log_file_name
                    
                    # 新規行を読み込み
                    new_lines = self._check_log_file(log_file_path)
                    
                    if new_lines:
                        # アラート検出
                        alerts = self._detect_alerts(log_file_name, new_lines)
                        
                        # アラート処理
                        for alert in alerts:
                            self._issue_alert(alert)
                
                # アラート履歴を保存
                self._save_alert_history()
                
            except Exception as e:
                self.logger.error(f"ログ監視エラー: {e}")
            
            # 監視間隔
            time.sleep(CONFIG["check_interval"])
    
    def generate_report(self):
        """監視レポートを生成"""
        report = f"""
================================================================================
          ManaOS ログ監視レポート
================================================================================
生成時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

================================================================================
監視ファイル
================================================================================
"""
        
        for log_file_name in CONFIG["watch_files"]:
            log_file_path = CONFIG["log_dir"] / log_file_name
            if log_file_path.exists():
                size = log_file_path.stat().st_size
                size_mb = size / (1024 * 1024)
                mtime = datetime.fromtimestamp(log_file_path.stat().st_mtime)
                report += f"[OK] {log_file_name}\n"
                report += f"     サイズ: {size_mb:.2f} MB\n"
                report += f"     更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
            else:
                report += f"[!] {log_file_name} (未作成)\n"
        
        report += f"\n================================================================================\nアラート統計\n================================================================================\n"
        
        if self.alert_history:
            for alert_key, info in sorted(
                self.alert_history.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:10]:  # 上位10件
                report += f"\n{alert_key}\n"
                report += f"  発生回数: {info['count']}\n"
                report += f"  初回: {info['first_time']}\n"
                report += f"  最終: {info['last_time']}\n"
        else:
            report += "[OK] アラートはありません\n"
        
        report += f"\n================================================================================\n"
        
        return report

def main():
    # ディレクトリ作成
    CONFIG["log_dir"].mkdir(exist_ok=True)
    
    # ロガー起動
    watcher = LogWatcher()
    
    # 初期レポート表示
    print("\n" + "="*60)
    print("ManaOS ログ監視・アラートシステム")
    print("="*60)
    print(f"監視ディレクトリ: {CONFIG['log_dir'].absolute()}")
    print(f"監視ファイル: {', '.join(CONFIG['watch_files'])}")
    print(f"チェック間隔: {CONFIG['check_interval']}秒")
    print("="*60 + "\n")
    
    # レポート表示
    print(watcher.generate_report())
    
    # 監視開始
    try:
        watcher.watch_logs()
    except KeyboardInterrupt:
        print("\n[OK] ログ監視を終了しました")
        watcher.logger.info("ログ監視を終了しました")

if __name__ == "__main__":
    main()
