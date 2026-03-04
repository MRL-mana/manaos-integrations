#!/usr/bin/env python3
"""
Mana Voice Assistant
AI音声アシスタント - 音声でシステム操作・状態確認
"""

import json
import logging
import subprocess
from typing import Dict, Any
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaVoiceAssistant:
    def __init__(self):
        self.name = "Mana"
        self.version = "1.0.0"
        
        # システムAPI
        self.api_endpoints = {
            "unified_dashboard": "http://localhost:9999/api/overview",
            "screen_sharing": "http://localhost:5008/api/status",
            "trinity_secretary": "http://localhost:8889/api/status",
            "security_audit": "/root/security_audit_enhanced.py",
            "auto_optimizer": "/root/mana_auto_optimizer.py",
            "log_analyzer": "/root/mana_smart_log_analyzer.py"
        }
        
        # 音声コマンドマッピング
        self.command_patterns = {
            "status": ["状態", "ステータス", "どう", "調子"],
            "task": ["タスク", "todo", "やること"],
            "schedule": ["予定", "スケジュール", "カレンダー"],
            "security": ["セキュリティ", "安全", "脆弱性"],
            "optimize": ["最適化", "クリーンアップ", "掃除"],
            "logs": ["ログ", "エラー", "問題"],
            "help": ["ヘルプ", "助けて", "できること"]
        }
        
        logger.info("🎤 Mana Voice Assistant 初期化完了")
    
    def process_text_command(self, text: str) -> Dict[str, Any]:
        """テキストコマンド処理（音声認識の代わり）"""
        text_lower = text.lower()
        
        # コマンド判定
        command = self._detect_command(text_lower)
        
        if command == "status":
            return self.get_system_status()
        
        elif command == "task":
            return self.get_tasks()
        
        elif command == "schedule":
            return self.get_schedule()
        
        elif command == "security":
            return self.get_security_status()
        
        elif command == "optimize":
            return self.run_optimization()
        
        elif command == "logs":
            return self.analyze_logs()
        
        elif command == "help":
            return self.get_help()
        
        else:
            # 自然言語処理（簡易版）
            return self.process_natural_language(text)
    
    def _detect_command(self, text: str) -> str:
        """コマンド検出"""
        for command, patterns in self.command_patterns.items():
            if any(pattern in text for pattern in patterns):
                return command
        return "unknown"
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        try:
            response = requests.get(self.api_endpoints["unified_dashboard"], timeout=5)
            data = response.json()
            
            metrics = data.get("system_metrics", {})
            services = data.get("services", {})
            security = data.get("security", {})
            
            # 音声応答テキスト生成
            cpu_status = "良好" if metrics["cpu"]["percent"] < 50 else "高負荷"
            memory_status = "正常" if metrics["memory"]["percent"] < 80 else "圧迫"
            disk_status = "十分" if metrics["disk"]["percent"] < 80 else "不足"
            
            response_text = f"""
システム状態を報告します。

CPU使用率: {metrics['cpu']['percent']:.1f}% - {cpu_status}
メモリ使用率: {metrics['memory']['percent']:.1f}% - {memory_status}
ディスク使用率: {metrics['disk']['percent']:.1f}% - {disk_status}

稼働サービス: {services['online']}/{services['total']}個
セキュリティスコア: {security['score']}/100

{self._get_status_summary(metrics, services, security)}
            """.strip()
            
            return {
                "success": True,
                "command": "status",
                "data": data,
                "response_text": response_text,
                "voice_ready": True
            }
            
        except Exception as e:
            logger.error(f"システム状態取得エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "response_text": "申し訳ありません。システム状態の取得に失敗しました。"
            }
    
    def _get_status_summary(self, metrics: Dict, services: Dict, security: Dict) -> str:
        """状態サマリー生成"""
        issues = []
        
        if metrics["cpu"]["percent"] > 80:
            issues.append("CPU使用率が高くなっています")
        
        if metrics["memory"]["percent"] > 80:
            issues.append("メモリが圧迫されています")
        
        if metrics["disk"]["percent"] > 85:
            issues.append("ディスク容量が不足しています")
        
        if services["online"] < services["total"]:
            offline = services["total"] - services["online"]
            issues.append(f"{offline}個のサービスが停止しています")
        
        if security["score"] < 60:
            issues.append("セキュリティスコアが低いです")
        
        if issues:
            return "注意事項: " + "、".join(issues)
        else:
            return "全システム正常に稼働中です。"
    
    def get_tasks(self) -> Dict[str, Any]:
        """タスク一覧取得"""
        try:
            response = requests.get("http://localhost:8889/api/tasks", timeout=5)
            tasks = response.json().get("tasks", [])
            
            if not tasks:
                response_text = "現在、タスクはありません。"
            else:
                pending_tasks = [t for t in tasks if t.get("status") == "pending"]
                high_priority = [t for t in pending_tasks if t.get("priority") == "high"]
                
                response_text = f"""
タスク状況を報告します。

全タスク: {len(tasks)}件
未完了: {len(pending_tasks)}件
高優先度: {len(high_priority)}件

{"高優先度タスク: " + ", ".join([t["title"][:30] for t in high_priority[:3]]) if high_priority else "高優先度タスクはありません"}
                """.strip()
            
            return {
                "success": True,
                "command": "task",
                "data": {"tasks": tasks},
                "response_text": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_text": "タスクの取得に失敗しました。"
            }
    
    def get_schedule(self) -> Dict[str, Any]:
        """予定取得"""
        response_text = """
カレンダー機能は現在開発中です。
Trinity秘書システムで予定管理が可能です。
        """.strip()
        
        return {
            "success": True,
            "command": "schedule",
            "response_text": response_text
        }
    
    def get_security_status(self) -> Dict[str, Any]:
        """セキュリティ状態取得"""
        try:
            # 最新の監査レポート読み込み
            import glob
            reports = sorted(glob.glob("/root/security_audit_reports/security_audit_*.json"), reverse=True)
            
            if not reports:
                return {
                    "success": False,
                    "response_text": "セキュリティ監査レポートが見つかりません。"
                }
            
            with open(reports[0], 'r') as f:
                report = json.load(f)
            
            score = report.get("security_score", 0)
            issues = report.get("issues", {})
            
            response_text = f"""
セキュリティ状態を報告します。

セキュリティスコア: {score}/100
ステータス: {report.get('status', 'unknown')}

検出された問題:
- Critical: {issues.get('critical', 0)}件
- High: {issues.get('high', 0)}件
- Medium: {issues.get('medium', 0)}件

{self._get_security_recommendation(score)}
            """.strip()
            
            return {
                "success": True,
                "command": "security",
                "data": report,
                "response_text": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_text": "セキュリティ状態の取得に失敗しました。"
            }
    
    def _get_security_recommendation(self, score: int) -> str:
        """セキュリティ推奨事項"""
        if score >= 80:
            return "セキュリティ状態は良好です。"
        elif score >= 60:
            return "セキュリティは改善の余地があります。"
        elif score >= 40:
            return "セキュリティ対策の強化を推奨します。"
        else:
            return "緊急のセキュリティ対策が必要です。"
    
    def run_optimization(self) -> Dict[str, Any]:
        """最適化実行"""
        try:
            result = subprocess.run(
                ["python3", self.api_endpoints["auto_optimizer"], "check"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            data = json.loads(result.stdout)
            optimizations = data.get("optimizations", [])
            
            if not optimizations:
                response_text = "システムは最適な状態です。最適化は不要です。"
            else:
                response_text = f"{len(optimizations)}個の最適化を実行しました。"
            
            return {
                "success": True,
                "command": "optimize",
                "data": data,
                "response_text": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_text": "最適化の実行に失敗しました。"
            }
    
    def analyze_logs(self) -> Dict[str, Any]:
        """ログ分析"""
        try:
            result = subprocess.run(
                ["python3", self.api_endpoints["log_analyzer"], "analyze"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            data = json.loads(result.stdout)
            
            response_text = f"""
ログ分析結果を報告します。

分析ファイル数: {data.get('total_files', 0)}
Critical: {data.get('total_critical', 0)}件
Error: {data.get('total_errors', 0)}件
Warning: {data.get('total_warnings', 0)}件
異常検出: {len(data.get('anomalies', []))}件

{self._get_log_summary(data)}
            """.strip()
            
            return {
                "success": True,
                "command": "logs",
                "data": data,
                "response_text": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_text": "ログ分析に失敗しました。"
            }
    
    def _get_log_summary(self, data: Dict) -> str:
        """ログサマリー"""
        if data.get("total_critical", 0) > 0:
            return "Criticalエラーが検出されています。早急な対応が必要です。"
        elif data.get("total_errors", 0) > 10:
            return "エラーが多数検出されています。確認を推奨します。"
        elif len(data.get("anomalies", [])) > 0:
            return "異常なパターンが検出されています。"
        else:
            return "ログに重大な問題は見つかりませんでした。"
    
    def get_help(self) -> Dict[str, Any]:
        """ヘルプ情報"""
        response_text = """
Mana音声アシスタントです。以下のコマンドが利用できます：

1. 状態確認: 「システムの状態を教えて」
2. タスク確認: 「タスクを教えて」
3. 予定確認: 「今日の予定は？」
4. セキュリティ: 「セキュリティ状態は？」
5. 最適化: 「システムを最適化して」
6. ログ分析: 「ログを分析して」

何かお手伝いできることはありますか？
        """.strip()
        
        return {
            "success": True,
            "command": "help",
            "response_text": response_text
        }
    
    def process_natural_language(self, text: str) -> Dict[str, Any]:
        """自然言語処理（簡易版）"""
        # 簡易的なキーワードマッチング
        if any(word in text for word in ["ありがとう", "感謝", "助かる"]):
            response_text = "どういたしまして！いつでもお手伝いします。"
        
        elif any(word in text for word in ["こんにちは", "やあ", "おはよう"]):
            response_text = "こんにちは！Manaです。何かお手伝いできることはありますか？"
        
        else:
            response_text = "申し訳ありません。理解できませんでした。「ヘルプ」と言ってください。"
        
        return {
            "success": True,
            "command": "chat",
            "response_text": response_text
        }

def main():
    assistant = ManaVoiceAssistant()
    
    import sys
    if len(sys.argv) > 1:
        # コマンドライン引数からテキスト取得
        text = " ".join(sys.argv[1:])
        result = assistant.process_text_command(text)
        
        print("\n" + "=" * 60)
        print("🎤 Mana Voice Assistant")
        print("=" * 60)
        print(f"\n入力: {text}")
        print(f"\nコマンド: {result.get('command', 'unknown')}")
        print(f"\n応答:\n{result.get('response_text', '')}")
        print("\n" + "=" * 60)
    else:
        # インタラクティブモード
        print("\n🎤 Mana Voice Assistant - インタラクティブモード")
        print("「exit」で終了\n")
        
        while True:
            try:
                text = input("あなた: ")
                if text.lower() in ["exit", "quit", "終了"]:
                    print("またね！")
                    break
                
                result = assistant.process_text_command(text)
                print(f"\nMana: {result.get('response_text', '')}\n")
                
            except KeyboardInterrupt:
                print("\nまたね！")
                break

if __name__ == "__main__":
    main()

