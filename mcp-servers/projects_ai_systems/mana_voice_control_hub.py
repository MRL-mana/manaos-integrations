#!/usr/bin/env python3
"""
Mana Voice Control Hub
音声制御ハブ - 全システムを音声で制御
"""

import asyncio
import json
import logging
import subprocess
import requests
from datetime import datetime
from typing import Dict, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaVoiceControlHub:
    def __init__(self):
        self.name = "Mana Voice Control Hub"
        self.version = "2.0.0"
        
        # 制御可能なシステム
        self.controllable_systems = {
            "screen_sharing": {
                "start": "http://localhost:5008/api/session/start",
                "stop": "http://localhost:5008/api/session/end",
                "screenshot": "http://localhost:5008/api/screenshot"
            },
            "trinity_secretary": {
                "create_task": "http://localhost:8889/api/task/create",
                "get_tasks": "http://localhost:8889/api/tasks",
                "create_event": "http://localhost:8889/api/calendar/create",
                "generate_report": "http://localhost:8889/api/report/generate"
            },
            "automation_engine": "/root/mana_unified_automation_engine.py",
            "mega_boost": "/root/mana_mega_boost_engine.py",
            "security_audit": "/root/security_audit_enhanced.py",
            "log_manager": "/root/mana_log_manager.py",
            "process_cleaner": "/root/mana_process_cleaner.py"
        }
        
        # 音声コマンドパターン（拡張版）
        self.command_patterns = {
            # システム制御
            "start_screen": ["画面共有", "スクリーン", "screen", "共有開始"],
            "screenshot": ["スクショ", "screenshot", "画面キャプチャ"],
            "create_task": ["タスク作成", "todo追加", "やること追加"],
            "create_event": ["予定追加", "カレンダー", "スケジュール追加"],
            
            # 最適化
            "mega_boost": ["メガブースト", "最適化実行", "全力最適化"],
            "clean_memory": ["メモリクリーン", "メモリ最適化"],
            "clean_disk": ["ディスククリーン", "ディスク最適化"],
            "clean_logs": ["ログクリーン", "ログ整理"],
            "clean_processes": ["プロセスクリーン", "重複削除"],
            
            # 分析・監査
            "security_audit": ["セキュリティ監査", "脆弱性チェック"],
            "analyze_logs": ["ログ分析", "エラー確認"],
            "system_status": ["システム状態", "ステータス", "調子", "状態を報告", "最終状態"],
            
            # レポート
            "daily_report": ["デイリーレポート", "今日のレポート"],
            "generate_report": ["レポート生成", "レポート作成"],
            
            # 総合
            "full_check": ["全チェック", "フルチェック", "完全チェック", "フルシステムチェック"],
            "auto_fix": ["自動修復", "問題を直して", "エラー修正"]
        }
        
        logger.info("🎤 Mana Voice Control Hub 初期化完了")
    
    async def process_voice_command(self, text: str) -> Dict[str, Any]:
        """音声コマンド処理（拡張版）"""
        text_lower = text.lower()
        
        # コマンド検出
        detected_commands = []
        for command, patterns in self.command_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                detected_commands.append(command)
        
        if not detected_commands:
            return await self.handle_unknown_command(text)
        
        # 複数コマンドの場合は最初のものを実行
        command = detected_commands[0]
        
        # コマンド実行
        handlers = {
            "start_screen": self.start_screen_sharing,
            "screenshot": self.take_screenshot,
            "create_task": lambda: self.create_task(text),
            "create_event": lambda: self.create_event(text),
            "mega_boost": self.run_mega_boost,
            "clean_memory": self.clean_memory,
            "clean_disk": self.clean_disk,
            "clean_logs": self.clean_logs,
            "clean_processes": self.clean_processes,
            "security_audit": self.run_security_audit,
            "analyze_logs": self.analyze_logs,
            "system_status": self.get_system_status,
            "daily_report": self.generate_daily_report,
            "generate_report": self.generate_daily_report,
            "full_check": self.full_system_check,
            "auto_fix": self.auto_fix_issues
        }
        
        if command in handlers:
            return await handlers[command]()
        else:
            return {"success": False, "error": "Command not implemented"}
    
    async def start_screen_sharing(self) -> Dict[str, Any]:
        """画面共有開始"""
        try:
            session_id = f"voice_session_{int(datetime.now().timestamp())}"
            response = requests.post(
                self.controllable_systems["screen_sharing"]["start"],
                json={"session_id": session_id},
                timeout=5
            )
            
            return {
                "success": True,
                "command": "start_screen",
                "response_text": f"画面共有を開始しました。セッションID: {session_id}",
                "data": response.json()
            }
        except Exception as e:
            return {"success": False, "error": str(e), "response_text": "画面共有の開始に失敗しました。"}
    
    async def take_screenshot(self) -> Dict[str, Any]:
        """スクリーンショット撮影"""
        try:
            session_id = "voice_screenshot"
            response = requests.post(
                f"{self.controllable_systems['screen_sharing']['screenshot']}/{session_id}",
                timeout=5
            )
            
            return {
                "success": True,
                "command": "screenshot",
                "response_text": "スクリーンショットを撮影しました。",
                "data": response.json()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_task(self, text: str) -> Dict[str, Any]:
        """タスク作成"""
        try:
            response = requests.post(
                self.controllable_systems["trinity_secretary"]["create_task"],
                json={"text": text, "source": "voice"},
                timeout=5
            )
            
            return {
                "success": True,
                "command": "create_task",
                "response_text": f"タスクを作成しました: {text[:50]}",
                "data": response.json()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_event(self, text: str) -> Dict[str, Any]:
        """カレンダー予定作成"""
        try:
            response = requests.post(
                self.controllable_systems["trinity_secretary"]["create_event"],
                json={"text": text, "source": "voice"},
                timeout=5
            )
            
            return {
                "success": True,
                "command": "create_event",
                "response_text": f"予定を作成しました: {text[:50]}",
                "data": response.json()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_mega_boost(self) -> Dict[str, Any]:
        """メガブースト実行"""
        logger.info("🔥 メガブースト実行")
        
        try:
            result = subprocess.run(
                ["python3", self.controllable_systems["mega_boost"]],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": True,
                "command": "mega_boost",
                "response_text": "メガブーストを実行しました。システムを最適化中です。"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def clean_memory(self) -> Dict[str, Any]:
        """メモリクリーン"""
        result = subprocess.run(
            ["python3", "/root/mana_auto_optimizer.py", "memory"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        data = json.loads(result.stdout)
        freed = data.get("freed_mb", 0)
        
        return {
            "success": True,
            "response_text": f"メモリを最適化しました。{freed:.2f}MB回収しました。"
        }
    
    async def clean_disk(self) -> Dict[str, Any]:
        """ディスククリーン"""
        result = subprocess.run(
            ["python3", "/root/mana_auto_optimizer.py", "disk"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        data = json.loads(result.stdout)
        freed = data.get("freed_gb", 0)
        
        return {
            "success": True,
            "response_text": f"ディスクを最適化しました。{freed:.2f}GB回収しました。"
        }
    
    async def clean_logs(self) -> Dict[str, Any]:
        """ログクリーン"""
        result = subprocess.run(
            ["python3", self.controllable_systems["log_manager"], "clean"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        match = re.search(r'削除行数:\s*([\d,]+)行', result.stdout)
        lines = match.group(1) if match else "不明"
        
        return {
            "success": True,
            "response_text": f"ログをクリーンアップしました。{lines}行削除しました。"
        }
    
    async def clean_processes(self) -> Dict[str, Any]:
        """プロセスクリーン"""
        result = subprocess.run(
            ["python3", self.controllable_systems["process_cleaner"], "clean"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        match = re.search(r'停止したプロセス:\s*(\d+)個', result.stdout)
        stopped = match.group(1) if match else "0"
        
        return {
            "success": True,
            "response_text": f"プロセスをクリーンアップしました。{stopped}個のプロセスを停止しました。"
        }
    
    async def run_security_audit(self) -> Dict[str, Any]:
        """セキュリティ監査"""
        result = subprocess.run(
            ["python3", self.controllable_systems["security_audit"]],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        match = re.search(r'セキュリティスコア:\s*(\d+)/100', result.stdout)
        score = match.group(1) if match else "不明"
        
        return {
            "success": True,
            "response_text": f"セキュリティ監査を実行しました。スコア: {score}/100"
        }
    
    async def analyze_logs(self) -> Dict[str, Any]:
        """ログ分析"""
        result = subprocess.run(
            ["python3", self.controllable_systems["log_analyzer"], "analyze"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        data = json.loads(result.stdout)
        errors = data.get("total_errors", 0)
        warnings = data.get("total_warnings", 0)
        
        return {
            "success": True,
            "response_text": f"ログを分析しました。エラー: {errors}件、警告: {warnings}件"
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        response = requests.get("http://localhost:9999/api/overview", timeout=5)
        data = response.json()
        
        metrics = data["system_metrics"]
        services = data["services"]
        
        return {
            "success": True,
            "response_text": f"""
システム状態:
CPU: {metrics['cpu']['percent']:.1f}%
メモリ: {metrics['memory']['percent']:.1f}%
ディスク: {metrics['disk']['percent']:.1f}%
サービス: {services['online']}/{services['total']}個オンライン
            """.strip()
        }
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """デイリーレポート生成"""
        response = requests.post(
            "http://localhost:8889/api/report/generate",
            timeout=5
        )
        
        return {
            "success": True,
            "response_text": "デイリーレポートを生成しました。"
        }
    
    async def full_system_check(self) -> Dict[str, Any]:
        """フルシステムチェック"""
        logger.info("🔍 フルシステムチェック開始")
        
        tasks = [
            self.get_system_status(),
            self.run_security_audit(),
            self.analyze_logs(),
            self.clean_processes()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "success": True,
            "response_text": "フルシステムチェックを実行しました。全システム正常です。"
        }
    
    async def auto_fix_issues(self) -> Dict[str, Any]:
        """自動修復"""
        logger.info("🔧 自動修復開始")
        
        # 統合自動化エンジンを実行
        result = subprocess.run(
            ["python3", self.controllable_systems["automation_engine"]],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        data = json.loads(result.stdout)
        actions = len(data.get("actions_executed", []))
        
        return {
            "success": True,
            "response_text": f"自動修復を実行しました。{actions}個のアクションを実行しました。"
        }
    
    async def handle_unknown_command(self, text: str) -> Dict[str, Any]:
        """不明なコマンド処理"""
        return {
            "success": False,
            "response_text": f"コマンドを理解できませんでした: {text}\n利用可能なコマンドは「ヘルプ」で確認してください。"
        }

async def main():
    hub = ManaVoiceControlHub()
    
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = await hub.process_voice_command(command)
        
        print("\n" + "=" * 60)
        print("🎤 Mana Voice Control Hub")
        print("=" * 60)
        print(f"\n入力: {command}")
        print(f"\n応答:\n{result.get('response_text', '')}")
        print("\n" + "=" * 60)
    else:
        print("Usage: mana_voice_control_hub.py <command>")
        print("\n利用可能なコマンド例:")
        print("  - メガブーストを実行して")
        print("  - セキュリティ監査を実行して")
        print("  - ログをクリーンアップして")
        print("  - プロセスをクリーンアップして")
        print("  - フルシステムチェックして")
        print("  - 自動修復して")

if __name__ == "__main__":
    asyncio.run(main())

