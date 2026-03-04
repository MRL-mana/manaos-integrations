#!/usr/bin/env python3
"""
Trinity Orchestrator - Self Learning Engine
自己改善ループ・Success Pattern学習
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

from ticket_manager import TicketManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_learning")


class SelfLearningEngine:
    """自己学習エンジン"""
    
    def __init__(self, obsidian_vault="/root/obsidian_vault", use_byterover=True):
        """
        初期化
        
        Args:
            obsidian_vault: Obsidianボールトパス
            use_byterover: Byterover MCPを使用するか
        """
        self.vault_path = obsidian_vault
        self.patterns_dir = f"{obsidian_vault}/Trinity"
        self.success_patterns_file = f"{self.patterns_dir}/Success_Patterns.md"
        self.failure_log_file = f"{self.patterns_dir}/Failure_Log.md"
        
        # ディレクトリ作成
        os.makedirs(self.patterns_dir, exist_ok=True)
        
        # ファイル初期化
        if not os.path.exists(self.success_patterns_file):
            with open(self.success_patterns_file, "w") as f:
                f.write("# Trinity Success Patterns\n\n")
                f.write("このファイルには、Trinityが成功したタスクのパターンが記録されます。\n\n")
        
        if not os.path.exists(self.failure_log_file):
            with open(self.failure_log_file, "w") as f:
                f.write("# Trinity Failure Log\n\n")
                f.write("このファイルには、失敗したタスクと解決策が記録されます。\n\n")
        
        self.ticket_manager = TicketManager()
        
        # Byterover MCP
        self.use_byterover = use_byterover
        if use_byterover:
            try:
                # Byterover MCP を使用（将来的に統合）
                logger.info("✅ Byterover MCP integration ready")
            except Exception as e:
                logger.warning(f"⚠️ Byterover MCP not available: {e}")
                self.use_byterover = False
        
        logger.info("✅ Self-Learning Engine initialized")
    
    def record_success(self, ticket_id: str, auto_tag: bool = True):
        """
        成功パターンを記録（Self-Learning Tag付き）
        
        Args:
            ticket_id: チケットID
            auto_tag: 自動タグ付けするか
        """
        ticket = self.ticket_manager.get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"⚠️ Ticket not found: {ticket_id}")
            return
        
        # 成功のみ記録
        if ticket.get("final_status") != "completed":
            return
        
        confidence = ticket["status"]["confidence"]
        if confidence < 0.8:
            return  # 低いconfidenceは記録しない
        
        # Self-Learning Tag生成
        tags = []
        if auto_tag:
            tags = self._generate_tags(ticket)
        
        # パターン抽出
        pattern = {
            "ticket_id": ticket_id,
            "goal": ticket["goal"],
            "context": ticket["context"],
            "confidence": confidence,
            "turns": ticket["status"]["turn"],
            "artifacts": len(ticket.get("artifacts", [])),
            "timestamp": datetime.now().isoformat()
        }
        
        # Obsidianに記録（Self-Learning Tag付き）
        try:
            with open(self.success_patterns_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n")
                f.write(f"## {pattern['goal']}\n\n")
                f.write(f"- **Ticket**: `{ticket_id}`\n")
                f.write(f"- **Confidence**: {confidence:.2%}\n")
                f.write(f"- **Turns**: {pattern['turns']}\n")
                f.write(f"- **Files**: {pattern['artifacts']}\n")
                f.write(f"- **Context**: {', '.join(pattern['context'])}\n")
                f.write(f"- **Date**: {pattern['timestamp']}\n")
                
                # Self-Learning Tags
                if tags:
                    f.write(f"- **Tags**: {', '.join([f'#{tag}' for tag in tags])}\n")
                
                f.write(f"\n")
                
                # 実行履歴の要約
                f.write(f"### 実行フロー\n\n")
                for h in ticket.get("history", [])[:5]:  # 最初の5ターンのみ
                    role = h.get("role", "unknown")
                    action = h.get("action", "unknown")
                    f.write(f"{h['turn']}. **{role}** - {action}\n")
                
                f.write(f"\n")
                
                # 成功の鍵（Self-Learning）
                f.write(f"### 💡 成功の鍵\n\n")
                success_factors = self._extract_success_factors(ticket)
                for factor in success_factors:
                    f.write(f"- {factor}\n")
                
                f.write(f"\n")
            
            logger.info(f"✅ Success pattern recorded: {ticket_id}")
            
            # Byterover MCPにも保存（将来実装）
            if self.use_byterover:
                # TODO: byterover.store_knowledge(json.dumps(pattern))
                pass
                
        except Exception as e:
            logger.error(f"❌ Failed to record success: {e}")
    
    def record_failure(self, ticket_id: str, analysis: Optional[str] = None):
        """
        失敗ログを記録
        
        Args:
            ticket_id: チケットID
            analysis: 失敗分析（オプション）
        """
        ticket = self.ticket_manager.get_ticket(ticket_id)
        if not ticket:
            return
        
        # 失敗のみ記録
        if ticket.get("final_status") == "completed":
            return
        
        try:
            with open(self.failure_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n")
                f.write(f"## ❌ {ticket['goal']}\n\n")
                f.write(f"- **Ticket**: `{ticket_id}`\n")
                f.write(f"- **Status**: {ticket.get('final_status', 'unknown')}\n")
                f.write(f"- **Confidence**: {ticket['status']['confidence']:.2%}\n")
                f.write(f"- **Turns**: {ticket['status']['turn']}\n")
                f.write(f"- **Date**: {datetime.now().isoformat()}\n\n")
                
                if analysis:
                    f.write(f"### 分析\n\n{analysis}\n\n")
                
                # 最後のエラー情報
                last_error = None
                for h in reversed(ticket.get("history", [])):
                    output = h.get("output", {})
                    if isinstance(output, dict) and output.get("error"):
                        last_error = output["error"]
                        break
                
                if last_error:
                    f.write(f"### エラー\n\n```\n{last_error}\n```\n\n")
            
            logger.info(f"✅ Failure logged: {ticket_id}")
        except Exception as e:
            logger.error(f"❌ Failed to log failure: {e}")
    
    def get_success_patterns(self, limit: int = 10) -> List[Dict]:
        """
        最近の成功パターンを取得
        
        Args:
            limit: 取得件数
            
        Returns:
            成功パターンのリスト
        """
        patterns = []
        
        # クローズ済みチケットから成功パターンを抽出
        try:
            closed_tickets = list(self.ticket_manager.redis_client.smembers("tickets:closed"))
            
            for tid in closed_tickets:
                ticket = self.ticket_manager.get_ticket(tid)
                if ticket and ticket.get("final_status") == "completed":
                    confidence = ticket["status"]["confidence"]
                    if confidence >= 0.8:
                        patterns.append({
                            "ticket_id": tid,
                            "goal": ticket["goal"],
                            "confidence": confidence,
                            "turns": ticket["status"]["turn"],
                            "context": ticket.get("context", [])
                        })
            
            # confidenceでソート
            patterns.sort(key=lambda x: x["confidence"], reverse=True)
            return patterns[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get success patterns: {e}")
            return []
    
    def suggest_improvements(self, ticket_id: str) -> List[str]:
        """
        改善提案を生成
        
        Args:
            ticket_id: チケットID
            
        Returns:
            改善提案のリスト
        """
        ticket = self.ticket_manager.get_ticket(ticket_id)
        if not ticket:
            return []
        
        suggestions = []
        confidence = ticket["status"]["confidence"]
        
        # 低いconfidenceの場合
        if confidence < 0.7:
            suggestions.append("⚠️ Confidenceが低いため、計画を見直すべきです")
        
        # ターン数が多い場合
        if ticket["status"]["turn"] > 8:
            suggestions.append("⚠️ ターン数が多いため、計画を簡略化すべきです")
        
        # 成果物がない場合
        if len(ticket.get("artifacts", [])) == 0:
            suggestions.append("❌ ファイルが生成されていません。Lunaのプロンプトを確認すべきです")
        
        # 停滞の場合
        if ticket["status"].get("stagnation_count", 0) > 0:
            suggestions.append("⚠️ 停滞が検知されました。アプローチを変えるべきです")
        
        return suggestions
    
    def auto_improve_loop(self, interval: int = 300):
        """
        自動改善ループ（デーモンモード）
        
        Args:
            interval: チェック間隔（秒）
        """
        import time
        
        logger.info(f"🧠 Starting auto-improvement loop (interval: {interval}s)")
        
        processed_tickets = set()
        
        try:
            while True:
                # クローズ済みチケット取得
                closed_tickets = list(self.ticket_manager.redis_client.smembers("tickets:closed"))
                
                for tid in closed_tickets:
                    if tid in processed_tickets:
                        continue
                    
                    ticket = self.ticket_manager.get_ticket(tid)
                    if not ticket:
                        continue
                    
                    # 成功パターン記録
                    if ticket.get("final_status") == "completed":
                        self.record_success(tid)
                    else:
                        self.record_failure(tid)
                    
                    processed_tickets.add(tid)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("👋 Auto-improvement loop stopped")


    def _generate_tags(self, ticket: Dict) -> List[str]:
        """
        Self-Learning Tags を自動生成
        
        Args:
            ticket: チケットデータ
            
        Returns:
            タグリスト
        """
        tags = []
        
        goal = ticket["goal"].lower()
        context = [c.lower() for c in ticket.get("context", [])]
        
        # 言語タグ
        if any(lang in goal or lang in ' '.join(context) for lang in ["python", "パイソン"]):
            tags.append("python")
        if any(lang in goal or lang in ' '.join(context) for lang in ["javascript", "js"]):
            tags.append("javascript")
        
        # タイプタグ
        if any(word in goal for word in ["アプリ", "app", "application"]):
            tags.append("application")
        if any(word in goal for word in ["スクリプト", "script"]):
            tags.append("script")
        if any(word in goal for word in ["api", "サーバー", "server"]):
            tags.append("api")
        
        # 難易度タグ
        turns = ticket["status"]["turn"]
        if turns <= 2:
            tags.append("simple")
        elif turns <= 5:
            tags.append("moderate")
        else:
            tags.append("complex")
        
        # 品質タグ
        confidence = ticket["status"]["confidence"]
        if confidence >= 0.95:
            tags.append("high-quality")
        elif confidence >= 0.8:
            tags.append("good-quality")
        
        return tags
    
    def _extract_success_factors(self, ticket: Dict) -> List[str]:
        """
        成功要因を抽出
        
        Args:
            ticket: チケットデータ
            
        Returns:
            成功要因リスト
        """
        factors = []
        
        # 高いConfidence
        if ticket["status"]["confidence"] >= 0.9:
            factors.append(f"高いConfidence（{ticket['status']['confidence']:.0%}）を達成")
        
        # 少ないターン数
        if ticket["status"]["turn"] <= 4:
            factors.append(f"効率的な実行（{ticket['status']['turn']}ターン）")
        
        # ファイル生成成功
        if len(ticket.get("artifacts", [])) > 0:
            factors.append(f"{len(ticket['artifacts'])}個のファイルを正常に生成")
        
        # コンテキストが適切
        if len(ticket.get("context", [])) > 0:
            factors.append("明確なコンテキスト指定")
        
        return factors if factors else ["順調に完了"]

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trinity Self-Learning Engine")
    parser.add_argument("--mode", choices=["daemon", "analyze", "report"], default="daemon")
    parser.add_argument("--interval", type=int, default=300, help="デーモンモード間隔（秒）")
    
    args = parser.parse_args()
    
    engine = SelfLearningEngine()
    
    if args.mode == "daemon":
        # デーモンモード
        engine.auto_improve_loop(interval=args.interval)
    
    elif args.mode == "analyze":
        # 過去のチケットを分析
        patterns = engine.get_success_patterns(limit=10)
        print(f"\n📊 Success Patterns (Top 10):\n")
        for i, p in enumerate(patterns, 1):
            print(f"{i}. {p['goal']} (Confidence: {p['confidence']:.2%}, Turns: {p['turns']})")
    
    elif args.mode == "report":
        # レポート生成
        patterns = engine.get_success_patterns(limit=20)
        
        if patterns:
            avg_confidence = sum(p["confidence"] for p in patterns) / len(patterns)
            avg_turns = sum(p["turns"] for p in patterns) / len(patterns)
            
            print(f"\n📊 Trinity Learning Report\n")
            print(f"Total Success Patterns: {len(patterns)}")
            print(f"Average Confidence: {avg_confidence:.2%}")
            print(f"Average Turns: {avg_turns:.1f}")
            print(f"\nPatterns saved to: {engine.success_patterns_file}")
        else:
            print("まだ成功パターンがありません。")

