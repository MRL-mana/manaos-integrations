#!/usr/bin/env python3
"""
Mana Unified Automation Engine
統合自動化エンジン - 全システムを連携させた完全自律稼働
"""

import asyncio
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaUnifiedAutomationEngine:
    def __init__(self):
        self.name = "Mana Unified Automation Engine"
        self.version = "1.0.0"
        
        # 統合システムエンドポイント
        self.systems = {
            "dashboard": "http://localhost:9999/api/overview",
            "screen_sharing": "http://localhost:5008/api/status",
            "trinity_secretary": "http://localhost:8889/api/status",
            "auto_optimizer": "/root/mana_auto_optimizer.py",
            "log_analyzer": "/root/mana_smart_log_analyzer.py",
            "security_audit": "/root/security_audit_enhanced.py",
            "process_cleaner": "/root/mana_process_cleaner.py",
            "log_manager": "/root/mana_log_manager.py",
            "notification": "/root/mana_notification_system.py",
            "voice_assistant": "/root/mana_voice_assistant.py",
            "mega_boost": "/root/mana_mega_boost_engine.py"
        }
        
        # 自動化ルール
        self.automation_rules = [
            {
                "name": "高CPU使用率対策",
                "condition": lambda metrics: metrics.get("cpu", {}).get("percent", 0) > 80,
                "action": "optimize_cpu",
                "priority": "high"
            },
            {
                "name": "高メモリ使用率対策",
                "condition": lambda metrics: metrics.get("memory", {}).get("percent", 0) > 80,
                "action": "optimize_memory",
                "priority": "high"
            },
            {
                "name": "ディスク容量警告",
                "condition": lambda metrics: metrics.get("disk", {}).get("percent", 0) > 85,
                "action": "optimize_disk",
                "priority": "critical"
            },
            {
                "name": "低セキュリティスコア",
                "condition": lambda security: security.get("score", 100) < 50,
                "action": "run_security_audit",
                "priority": "high"
            },
            {
                "name": "重複プロセス検出",
                "condition": lambda processes: processes.get("duplicates", 0) > 5,
                "action": "clean_processes",
                "priority": "medium"
            }
        ]
        
        logger.info("🤖 Mana Unified Automation Engine 初期化完了")
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """全システムの状態を取得"""
        try:
            response = requests.get(self.systems["dashboard"], timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"システム状態取得エラー: {e}")
            return {}
    
    async def check_automation_rules(self, overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        """自動化ルールをチェック"""
        triggered_rules = []
        
        metrics = overview.get("system_metrics", {})
        security = overview.get("security", {})
        
        # 各ルールをチェック
        for rule in self.automation_rules:
            try:
                # ルール名に応じてデータを渡す
                if "セキュリティ" in rule["name"]:
                    condition_met = rule["condition"](security)
                elif "プロセス" in rule["name"]:
                    # プロセス情報を取得
                    result = subprocess.run(
                        ["python3", self.systems["process_cleaner"]],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    # 簡易的なチェック
                    condition_met = "クリーンアップ候補" in result.stdout
                else:
                    condition_met = rule["condition"](metrics)
                
                if condition_met:
                    triggered_rules.append(rule)
                    logger.warning(f"⚠️ ルール発火: {rule['name']}")
                    
            except Exception as e:
                logger.error(f"ルールチェックエラー ({rule['name']}): {e}")
        
        return triggered_rules
    
    async def execute_action(self, action: str) -> Dict[str, Any]:
        """アクションを実行"""
        logger.info(f"🔧 アクション実行: {action}")
        
        actions_map = {
            "optimize_cpu": self.optimize_cpu,
            "optimize_memory": self.optimize_memory,
            "optimize_disk": self.optimize_disk,
            "run_security_audit": self.run_security_audit,
            "clean_processes": self.clean_processes
        }
        
        if action in actions_map:
            return await actions_map[action]()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def optimize_cpu(self) -> Dict[str, Any]:
        """CPU最適化"""
        logger.info("⚡ CPU最適化開始")
        # プロセスクリーンアップを実行
        return await self.clean_processes()
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """メモリ最適化"""
        logger.info("🧹 メモリ最適化開始")
        
        try:
            result = subprocess.run(
                ["python3", self.systems["auto_optimizer"], "memory"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            data = json.loads(result.stdout)
            
            # 通知送信
            await self.send_notification(
                "メモリ最適化完了",
                f"回収: {data.get('freed_mb', 0):.2f}MB",
                "success"
            )
            
            return data
            
        except Exception as e:
            logger.error(f"メモリ最適化エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def optimize_disk(self) -> Dict[str, Any]:
        """ディスク最適化"""
        logger.info("💾 ディスク最適化開始")
        
        try:
            result = subprocess.run(
                ["python3", self.systems["auto_optimizer"], "disk"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            data = json.loads(result.stdout)
            
            # 通知送信
            await self.send_notification(
                "ディスク最適化完了",
                f"回収: {data.get('freed_gb', 0):.2f}GB",
                "success"
            )
            
            return data
            
        except Exception as e:
            logger.error(f"ディスク最適化エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_security_audit(self) -> Dict[str, Any]:
        """セキュリティ監査実行"""
        logger.info("🔐 セキュリティ監査開始")
        
        try:
            result = subprocess.run(
                ["python3", self.systems["security_audit"]],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # スコアを抽出
            import re
            score_match = re.search(r'セキュリティスコア:\s*(\d+)/100', result.stdout)
            score = int(score_match.group(1)) if score_match else 0
            
            # 通知送信
            level = "critical" if score < 40 else "warning" if score < 60 else "info"
            await self.send_notification(
                "セキュリティ監査完了",
                f"スコア: {score}/100",
                level
            )
            
            return {"success": True, "score": score}
            
        except Exception as e:
            logger.error(f"セキュリティ監査エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def clean_processes(self) -> Dict[str, Any]:
        """プロセスクリーンアップ"""
        logger.info("🧹 プロセスクリーンアップ開始")
        
        try:
            result = subprocess.run(
                ["python3", self.systems["process_cleaner"], "clean"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # 停止数を抽出
            import re
            match = re.search(r'停止したプロセス:\s*(\d+)個', result.stdout)
            stopped = int(match.group(1)) if match else 0
            
            if stopped > 0:
                await self.send_notification(
                    "プロセスクリーンアップ完了",
                    f"{stopped}個のプロセスを停止",
                    "success"
                )
            
            return {"success": True, "stopped": stopped}
            
        except Exception as e:
            logger.error(f"プロセスクリーンアップエラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_notification(self, title: str, message: str, level: str = "info"):
        """通知送信"""
        try:
            # Notification Systemを使用（環境変数設定済みの場合）
            # 今回はログのみ
            logger.info(f"📢 通知: [{level.upper()}] {title} - {message}")
        except Exception as e:
            logger.error(f"通知送信エラー: {e}")
    
    async def run_automation_cycle(self) -> Dict[str, Any]:
        """自動化サイクル実行"""
        logger.info("=" * 60)
        logger.info("🤖 統合自動化サイクル開始")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. システム状態取得
        overview = await self.get_system_overview()
        
        if not overview:
            return {"success": False, "error": "Failed to get overview"}
        
        # 2. 自動化ルールチェック
        triggered_rules = await self.check_automation_rules(overview)
        
        # 3. アクション実行
        actions_executed = []
        for rule in triggered_rules:
            logger.info(f"📋 実行中: {rule['name']} (優先度: {rule['priority']})")
            result = await self.execute_action(rule["action"])
            actions_executed.append({
                "rule": rule["name"],
                "action": rule["action"],
                "result": result
            })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✅ 自動化サイクル完了: {duration:.2f}秒")
        logger.info(f"実行アクション: {len(actions_executed)}個")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "duration_seconds": duration,
            "triggered_rules": len(triggered_rules),
            "actions_executed": actions_executed,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_continuous(self, interval: int = 300):
        """連続自動化モード（5分ごと）"""
        logger.info(f"🔄 連続自動化モード開始（{interval}秒間隔）")
        
        try:
            while True:
                await self.run_automation_cycle()
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("⏹️ 連続自動化モード停止")
        except Exception as e:
            logger.error(f"連続自動化エラー: {e}")

async def main():
    engine = ManaUnifiedAutomationEngine()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # 連続モード
        await engine.run_continuous()
    else:
        # 1回実行
        result = await engine.run_automation_cycle()
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())

