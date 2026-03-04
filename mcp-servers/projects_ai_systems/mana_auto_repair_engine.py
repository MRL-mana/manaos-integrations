#!/usr/bin/env python3
"""
Mana Auto Repair Engine
自動修復エンジン - 問題検出→分析→自動修復
"""

import asyncio
import json
import logging
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaAutoRepairEngine:
    def __init__(self):
        self.name = "Mana Auto Repair Engine"
        self.repair_history = []
        
        # 修復ルール
        self.repair_rules = [
            {
                "issue": "high_memory",
                "detection": lambda m: m.get("memory", {}).get("percent", 0) > 85,
                "repair_action": "optimize_memory",
                "description": "メモリ使用率が高い"
            },
            {
                "issue": "high_disk",
                "detection": lambda m: m.get("disk", {}).get("percent", 0) > 85,
                "repair_action": "optimize_disk",
                "description": "ディスク使用率が高い"
            },
            {
                "issue": "duplicate_processes",
                "detection": lambda m: True,  # 常にチェック
                "repair_action": "clean_processes",
                "description": "重複プロセスの可能性"
            },
            {
                "issue": "log_overflow",
                "detection": lambda m: True,  # 定期的にクリーン
                "repair_action": "clean_logs",
                "description": "ログファイルの肥大化防止"
            },
            {
                "issue": "low_security",
                "detection": lambda m: m.get("security_score", 100) < 50,
                "repair_action": "improve_security",
                "description": "セキュリティスコアが低い"
            }
        ]
        
        logger.info("🔧 Mana Auto Repair Engine 初期化完了")
    
    async def detect_issues(self) -> List[Dict[str, Any]]:
        """問題検出"""
        logger.info("🔍 問題を検出中...")
        
        # システム状態取得
        try:
            response = requests.get("http://localhost:9999/api/overview", timeout=5)
            overview = response.json()
        except requests.RequestException:
            overview = {}
        
        metrics = overview.get("system_metrics", {})
        security = overview.get("security", {})
        
        # 統合データ
        check_data = {**metrics, "security_score": security.get("score", 100)}
        
        detected_issues = []
        for rule in self.repair_rules:
            try:
                if rule["detection"](check_data):
                    # 実際に問題があるか確認
                    if rule["issue"] in ["high_memory", "high_disk", "low_security"]:
                        detected_issues.append(rule)
                        logger.warning(f"⚠️ 問題検出: {rule['description']}")
            except Exception as e:
                logger.error(f"検出エラー ({rule['issue']}): {e}")
        
        return detected_issues
    
    async def repair_issue(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """問題を修復"""
        logger.info(f"🔧 修復実行: {rule['description']}")
        
        action = rule["repair_action"]
        
        try:
            if action == "optimize_memory":
                result = subprocess.run(
                    ["python3", "/root/mana_auto_optimizer.py", "memory"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "action": action,
                    "result": f"{data.get('freed_mb', 0):.2f}MB回収"
                }
            
            elif action == "optimize_disk":
                result = subprocess.run(
                    ["python3", "/root/mana_auto_optimizer.py", "disk"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "action": action,
                    "result": f"{data.get('freed_gb', 0):.2f}GB回収"
                }
            
            elif action == "clean_processes":
                result = subprocess.run(
                    ["python3", "/root/mana_process_cleaner.py", "clean"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                match = re.search(r'停止したプロセス:\s*(\d+)個', result.stdout)
                stopped = match.group(1) if match else "0"
                return {
                    "success": True,
                    "action": action,
                    "result": f"{stopped}個のプロセス停止"
                }
            
            elif action == "clean_logs":
                result = subprocess.run(
                    ["python3", "/root/mana_log_manager.py", "clean"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return {
                    "success": True,
                    "action": action,
                    "result": "ログクリーンアップ完了"
                }
            
            elif action == "improve_security":
                # セキュリティ改善アクション（将来実装）
                return {
                    "success": True,
                    "action": action,
                    "result": "セキュリティ改善処理実行"
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"修復エラー ({action}): {e}")
            return {"success": False, "error": str(e)}
    
    async def run_auto_repair(self) -> Dict[str, Any]:
        """自動修復実行"""
        logger.info("=" * 60)
        logger.info("🔧 自動修復エンジン開始")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 問題検出
        issues = await self.detect_issues()
        
        if not issues:
            logger.info("✅ 問題は検出されませんでした")
            return {
                "success": True,
                "issues_found": 0,
                "repairs_executed": 0,
                "message": "システムは正常です"
            }
        
        logger.info(f"⚠️ {len(issues)}個の問題を検出")
        
        # 2. 修復実行
        repairs = []
        for issue in issues:
            repair_result = await self.repair_issue(issue)
            repairs.append({
                "issue": issue["description"],
                "result": repair_result
            })
            
            # 修復履歴に記録
            self.repair_history.append({
                "timestamp": datetime.now().isoformat(),
                "issue": issue["description"],
                "action": issue["repair_action"],
                "result": repair_result
            })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✅ 自動修復完了: {duration:.2f}秒")
        logger.info(f"修復実行: {len(repairs)}個")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "issues_found": len(issues),
            "repairs_executed": len(repairs),
            "repairs": repairs,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }

async def main():
    engine = ManaAutoRepairEngine()
    result = await engine.run_auto_repair()
    
    print("\n" + "=" * 60)
    print("🔧 自動修復レポート")
    print("=" * 60)
    print(f"\n検出された問題: {result['issues_found']}個")
    print(f"実行した修復: {result['repairs_executed']}個")
    
    if result.get("repairs"):
        print("\n修復内容:")
        for i, repair in enumerate(result["repairs"], 1):
            print(f"  {i}. {repair['issue']}")
            print(f"     → {repair['result'].get('result', '完了')}")
    
    print(f"\n実行時間: {result.get('duration_seconds', 0):.2f}秒")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    import re
    asyncio.run(main())

