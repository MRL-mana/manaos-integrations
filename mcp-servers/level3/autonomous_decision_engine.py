#!/usr/bin/env python3
"""
完全自律判断エンジン - Level 3
人間の承認なしで自動的に判断・実装
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from enum import Enum
import sys

sys.path.insert(0, '/root')
from mcp_integration_hub import MCPIntegrationHub
from ai_trinity_auto_dev_system import AITrinityAutoDevSystem

class RiskLevel(Enum):
    """リスクレベル"""
    CRITICAL = "critical"      # データベース変更等
    HIGH = "high"              # API破壊的変更
    MEDIUM = "medium"          # 機能追加
    LOW = "low"                # UI変更、ドキュメント
    MINIMAL = "minimal"        # テスト、コメント

class DecisionAction(Enum):
    """判断結果のアクション"""
    AUTO_IMPLEMENT = "auto_implement"           # 即座に自動実装
    AUTO_WITH_NOTIFY = "auto_with_notify"       # 実装後に通知
    REQUEST_APPROVAL = "request_approval"       # 人間の承認待ち
    REJECT = "reject"                           # 却下

class AutonomousDecisionEngine:
    """完全自律判断エンジン"""
    
    def __init__(self):
        self.hub = MCPIntegrationHub()
        self.trinity = AITrinityAutoDevSystem()
        self.decision_log = Path("/root/level3/decision_log.json")
        self.config = self._load_config()
        self.ensure_log()
    
    def _load_config(self) -> Dict:
        """設定読み込み"""
        config_file = Path("/root/level3/level3_config.json")
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # デフォルト設定
        default_config = {
            "auto_implement_threshold": 0.95,      # 信頼度95%以上で自動実装
            "auto_notify_threshold": 0.80,         # 信頼度80%以上で実装後通知
            "risk_tolerance": {
                "minimal": "auto_implement",
                "low": "auto_implement",
                "medium": "auto_with_notify",
                "high": "request_approval",
                "critical": "request_approval"
            },
            "enable_autonomous": True,              # 自律判断を有効化
            "safe_mode": False,                     # 安全モード（全て承認待ち）
            "notification_channels": ["log", "slack"],
            "max_auto_implementations_per_hour": 5  # 1時間あたり最大5個まで自動実装
        }
        
        # 設定保存
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def ensure_log(self):
        """ログファイル初期化"""
        if not self.decision_log.exists():
            with open(self.decision_log, 'w') as f:
                json.dump({
                    "decisions": [],
                    "stats": {
                        "total": 0,
                        "auto_implemented": 0,
                        "auto_with_notify": 0,
                        "requested_approval": 0,
                        "rejected": 0
                    }
                }, f, indent=2)
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DECISION": "🤔",
            "AUTO": "🤖"
        }.get(level, "ℹ️")
        print(f"[{timestamp}] {emoji} {message}")
    
    async def calculate_confidence_score(self, proposal: Dict) -> float:
        """信頼度スコア計算"""
        score = 0.0
        
        # 1. 類似パターンの存在（40点）
        similar_patterns = await self.hub.ai_search_patterns(
            query=proposal['title'],
            limit=10
        )
        
        if similar_patterns['total'] > 0:
            # 類似パターンが多いほど信頼度高い
            pattern_score = min(similar_patterns['total'] / 10, 1.0) * 40
            score += pattern_score
        
        # 2. 実装の複雑度（30点）
        # 複雑度が低いほど信頼度高い
        complexity = proposal.get('complexity', 'medium')
        complexity_scores = {
            'simple': 30,
            'medium': 20,
            'complex': 10,
            'very_complex': 5
        }
        score += complexity_scores.get(complexity, 15)
        
        # 3. テストカバレッジ予測（20点）
        # テストが書きやすいほど信頼度高い
        testability = proposal.get('testability', 'medium')
        testability_scores = {
            'high': 20,
            'medium': 15,
            'low': 10
        }
        score += testability_scores.get(testability, 15)
        
        # 4. 過去の成功率（10点）
        with open(self.decision_log, 'r') as f:
            log_data = json.load(f)
        
        if log_data['stats']['total'] > 0:
            success_rate = (
                log_data['stats']['auto_implemented'] + 
                log_data['stats']['auto_with_notify']
            ) / log_data['stats']['total']
            score += success_rate * 10
        else:
            score += 7  # デフォルト
        
        return min(score / 100, 1.0)
    
    def assess_risk_level(self, proposal: Dict) -> RiskLevel:
        """リスクレベル評価"""
        category = proposal.get('category', 'unknown')
        
        # カテゴリ別リスク判定
        risk_map = {
            'database_schema': RiskLevel.CRITICAL,
            'api_breaking': RiskLevel.HIGH,
            'security': RiskLevel.CRITICAL,
            'data_migration': RiskLevel.CRITICAL,
            'api_addition': RiskLevel.MEDIUM,
            'feature_addition': RiskLevel.MEDIUM,
            'ui_change': RiskLevel.LOW,
            'documentation': RiskLevel.MINIMAL,
            'test': RiskLevel.MINIMAL,
            'refactoring': RiskLevel.MEDIUM,
            'bug_fix': RiskLevel.LOW,
            'performance': RiskLevel.MEDIUM
        }
        
        return risk_map.get(category, RiskLevel.MEDIUM)
    
    async def make_decision(self, proposal: Dict) -> Tuple[DecisionAction, Dict]:
        """自律判断を実行"""
        self.log(f"判断開始: {proposal['title']}", "DECISION")
        
        # 安全モードチェック
        if self.config['safe_mode']:
            self.log("安全モード: 全て承認待ち", "WARNING")
            return DecisionAction.REQUEST_APPROVAL, {
                "reason": "Safe mode enabled"
            }
        
        # 自律判断が無効
        if not self.config['enable_autonomous']:
            return DecisionAction.REQUEST_APPROVAL, {
                "reason": "Autonomous decision disabled"
            }
        
        # 1時間あたりの実装数制限チェック
        if not await self._check_rate_limit():
            self.log("レート制限: 1時間あたりの上限到達", "WARNING")
            return DecisionAction.REQUEST_APPROVAL, {
                "reason": "Rate limit exceeded"
            }
        
        # 信頼度スコア計算
        confidence = await self.calculate_confidence_score(proposal)
        self.log(f"信頼度スコア: {confidence:.1%}", "INFO")
        
        # リスクレベル評価
        risk_level = self.assess_risk_level(proposal)
        self.log(f"リスクレベル: {risk_level.value}", "INFO")
        
        # 判断ロジック
        decision_info = {
            "confidence": confidence,
            "risk_level": risk_level.value,
            "timestamp": datetime.now().isoformat()
        }
        
        # リスクレベルによる判断
        risk_action = self.config['risk_tolerance'].get(risk_level.value)
        
        if risk_action == "request_approval":
            self.log("判断: 承認待ち（リスク高）", "WARNING")
            return DecisionAction.REQUEST_APPROVAL, decision_info
        
        # 信頼度による判断
        if confidence >= self.config['auto_implement_threshold']:
            self.log("判断: 自動実装（信頼度高）", "AUTO")
            return DecisionAction.AUTO_IMPLEMENT, decision_info
        
        elif confidence >= self.config['auto_notify_threshold']:
            self.log("判断: 自動実装＋通知（信頼度中）", "AUTO")
            return DecisionAction.AUTO_WITH_NOTIFY, decision_info
        
        else:
            self.log("判断: 承認待ち（信頼度低）", "WARNING")
            return DecisionAction.REQUEST_APPROVAL, decision_info
    
    async def _check_rate_limit(self) -> bool:
        """レート制限チェック"""
        with open(self.decision_log, 'r') as f:
            log_data = json.load(f)
        
        # 過去1時間の自動実装数をカウント
        one_hour_ago = datetime.now().timestamp() - 3600
        recent_auto = sum(
            1 for decision in log_data['decisions']
            if decision.get('action') in ['auto_implement', 'auto_with_notify']
            and datetime.fromisoformat(decision['timestamp']).timestamp() > one_hour_ago
        )
        
        max_per_hour = self.config['max_auto_implementations_per_hour']
        return recent_auto < max_per_hour
    
    async def execute_decision(self, proposal: Dict, action: DecisionAction, decision_info: Dict) -> Dict:
        """判断結果を実行"""
        result = {
            "proposal": proposal,
            "action": action.value,
            "decision_info": decision_info,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        if action == DecisionAction.AUTO_IMPLEMENT:
            self.log("自動実装開始...", "AUTO")
            
            try:
                # Trinity自動開発システムで実装
                impl_result = await self.trinity.auto_develop(proposal['description'])
                
                result['status'] = 'completed'
                result['implementation'] = impl_result
                
                self.log(f"自動実装完了: {impl_result['implementation']['code_lines']}行", "SUCCESS")
                
            except Exception as e:
                self.log(f"自動実装失敗: {e}", "ERROR")
                result['status'] = 'failed'
                result['error'] = str(e)
        
        elif action == DecisionAction.AUTO_WITH_NOTIFY:
            self.log("自動実装＋通知開始...", "AUTO")
            
            try:
                # 実装
                impl_result = await self.trinity.auto_develop(proposal['description'])
                
                result['status'] = 'completed'
                result['implementation'] = impl_result
                
                # 通知
                await self._send_notification(
                    f"自動実装完了: {proposal['title']}",
                    f"信頼度: {decision_info['confidence']:.1%}\n"
                    f"コード: {impl_result['implementation']['code_lines']}行"
                )
                
                self.log("自動実装＋通知完了", "SUCCESS")
                
            except Exception as e:
                self.log(f"自動実装失敗: {e}", "ERROR")
                result['status'] = 'failed'
                result['error'] = str(e)
        
        elif action == DecisionAction.REQUEST_APPROVAL:
            self.log("承認待ち状態に設定", "WARNING")
            result['status'] = 'awaiting_approval'
            
            # 承認待ちキューに追加
            await self._add_to_approval_queue(proposal, decision_info)
        
        elif action == DecisionAction.REJECT:
            self.log("提案を却下", "WARNING")
            result['status'] = 'rejected'
        
        # ログに記録
        await self._record_decision(result)
        
        return result
    
    async def _send_notification(self, title: str, message: str):
        """通知送信"""
        channels = self.config['notification_channels']
        
        if 'log' in channels:
            # ログファイルに記録
            log_file = Path("/root/logs/autonomous_notifications.log")
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] {title}\n{message}\n\n")
        
        if 'slack' in channels:
            # Slack通知（実装済みのSlack Botを使用）
            try:
                # TODO: Slack Bot連携
                pass
            except:
                pass
    
    async def _add_to_approval_queue(self, proposal: Dict, decision_info: Dict):
        """承認待ちキューに追加"""
        queue_file = Path("/root/level3/approval_queue.json")
        
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                queue = json.load(f)
        else:
            queue = {"queue": []}
        
        queue['queue'].append({
            "proposal": proposal,
            "decision_info": decision_info,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        })
        
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
    
    async def _record_decision(self, result: Dict):
        """判断結果を記録"""
        with open(self.decision_log, 'r') as f:
            log_data = json.load(f)
        
        log_data['decisions'].append(result)
        log_data['stats']['total'] += 1
        
        action = result['action']
        if action == 'auto_implement':
            log_data['stats']['auto_implemented'] += 1
        elif action == 'auto_with_notify':
            log_data['stats']['auto_with_notify'] += 1
        elif action == 'request_approval':
            log_data['stats']['requested_approval'] += 1
        elif action == 'reject':
            log_data['stats']['rejected'] += 1
        
        with open(self.decision_log, 'w') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    async def get_decision_stats(self) -> Dict:
        """判断統計取得"""
        with open(self.decision_log, 'r') as f:
            log_data = json.load(f)
        
        stats = log_data['stats']
        
        if stats['total'] > 0:
            stats['auto_rate'] = (
                stats['auto_implemented'] + stats['auto_with_notify']
            ) / stats['total'] * 100
        else:
            stats['auto_rate'] = 0
        
        return stats

async def main():
    print("\n" + "=" * 70)
    print("🤖 完全自律判断エンジン - Level 3")
    print("=" * 70)
    
    engine = AutonomousDecisionEngine()
    
    # デモ: いくつかの提案を判断
    proposals = [
        {
            "title": "ログレベル設定機能追加",
            "description": "ログレベルを動的に変更できる機能",
            "category": "feature_addition",
            "complexity": "simple",
            "testability": "high"
        },
        {
            "title": "データベーススキーマ変更",
            "description": "ユーザーテーブルに新しいカラム追加",
            "category": "database_schema",
            "complexity": "medium",
            "testability": "medium"
        },
        {
            "title": "UIボタン色変更",
            "description": "プライマリボタンの色を青に変更",
            "category": "ui_change",
            "complexity": "simple",
            "testability": "high"
        }
    ]
    
    for proposal in proposals:
        print(f"\n{'-' * 70}")
        
        # 判断
        action, decision_info = await engine.make_decision(proposal)
        
        # 実行
        result = await engine.execute_decision(proposal, action, decision_info)
        
        print(f"結果: {result['status']}")
        
        await asyncio.sleep(1)
    
    # 統計表示
    print(f"\n{'=' * 70}")
    print("📊 判断統計")
    print(f"{'=' * 70}")
    
    stats = await engine.get_decision_stats()
    print(f"総判断数: {stats['total']}")
    print(f"自動実装: {stats['auto_implemented']}")
    print(f"自動実装＋通知: {stats['auto_with_notify']}")
    print(f"承認待ち: {stats['requested_approval']}")
    print(f"却下: {stats['rejected']}")
    print(f"自動化率: {stats['auto_rate']:.1f}%")
    
    print(f"\n{'=' * 70}")
    print("🎉 完了")
    print(f"{'=' * 70}")
    print(f"\n判断ログ: {engine.decision_log}")

if __name__ == "__main__":
    asyncio.run(main())

