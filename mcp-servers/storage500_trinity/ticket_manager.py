#!/usr/bin/env python3
"""
Trinity Orchestrator - Ticket Manager
Redisでチケット（タスク状態）を管理
"""

import json
import redis
from datetime import datetime
from typing import Dict, List, Optional, Any


class TicketManager:
    """Redisベースのチケット管理システム"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        """
        初期化
        
        Args:
            redis_host: Redisホスト
            redis_port: Redisポート
            redis_db: Redis DB番号
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
    def create_ticket(self, goal: str, context: List[str] = None, budget_turns: int = 12) -> str:
        """
        新規チケット作成
        
        Args:
            goal: 達成目標
            context: 前提条件・制約
            budget_turns: 最大ターン数
            
        Returns:
            ticket_id
        """
        ticket_id = f"T-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        ticket = {
            "ticket_id": ticket_id,
            "goal": goal,
            "context": context or [],
            "history": [],
            "artifacts": [],
            "status": {
                "stage": "init",  # init -> plan -> execute -> review -> done
                "turn": 0,
                "budget_turns": budget_turns,
                "confidence": 0.0,
                "stagnation_count": 0,
                "last_role": None,
                "same_role_count": 0
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Redisに保存
        self.redis_client.set(f"ticket:{ticket_id}", json.dumps(ticket, ensure_ascii=False))
        
        # アクティブチケットリストに追加
        self.redis_client.sadd("tickets:active", ticket_id)
        
        return ticket_id
    
    def get_ticket(self, ticket_id: str) -> Optional[Dict]:
        """
        チケット取得
        
        Args:
            ticket_id: チケットID
            
        Returns:
            チケットデータ（辞書）、存在しない場合はNone
        """
        data = self.redis_client.get(f"ticket:{ticket_id}")
        if data:
            return json.loads(data)
        return None
    
    def update_ticket(self, ticket_id: str, updates: Dict) -> bool:
        """
        チケット更新
        
        Args:
            ticket_id: チケットID
            updates: 更新内容（辞書）
            
        Returns:
            成功したらTrue
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        # 更新をマージ
        ticket.update(updates)
        ticket["updated_at"] = datetime.now().isoformat()
        
        # Redisに保存
        self.redis_client.set(f"ticket:{ticket_id}", json.dumps(ticket, ensure_ascii=False))
        return True
    
    def add_history(self, ticket_id: str, role: str, action: str, output: Any) -> bool:
        """
        履歴追加
        
        Args:
            ticket_id: チケットID
            role: 役割（remi/luna/mina）
            action: アクション（plan/execute/review）
            output: 出力内容
            
        Returns:
            成功したらTrue
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        # 履歴エントリ作成
        history_entry = {
            "turn": ticket["status"]["turn"] + 1,
            "role": role,
            "action": action,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        ticket["history"].append(history_entry)
        ticket["status"]["turn"] += 1
        
        # 同じ役割の連続カウント
        if ticket["status"]["last_role"] == role:
            ticket["status"]["same_role_count"] += 1
        else:
            ticket["status"]["same_role_count"] = 1
            ticket["status"]["last_role"] = role
        
        # 保存
        return self.update_ticket(ticket_id, ticket)
    
    def add_artifact(self, ticket_id: str, artifact_type: str, path: str, description: str = "") -> bool:
        """
        成果物追加
        
        Args:
            ticket_id: チケットID
            artifact_type: 成果物タイプ（file/url/data）
            path: パスまたはURI
            description: 説明
            
        Returns:
            成功したらTrue
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        artifact = {
            "type": artifact_type,
            "path": path,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        ticket["artifacts"].append(artifact)
        return self.update_ticket(ticket_id, ticket)
    
    def update_status(self, ticket_id: str, stage: str = None, confidence: float = None) -> bool:
        """
        ステータス更新
        
        Args:
            ticket_id: チケットID
            stage: ステージ（plan/execute/review/done）
            confidence: 信頼度（0-1）
            
        Returns:
            成功したらTrue
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        if stage:
            ticket["status"]["stage"] = stage
        if confidence is not None:
            ticket["status"]["confidence"] = confidence
        
        return self.update_ticket(ticket_id, ticket)
    
    def detect_stagnation(self, ticket_id: str) -> bool:
        """
        停滞検知
        
        同じ提案が3回続いたら停滞とみなす
        
        Args:
            ticket_id: チケットID
            
        Returns:
            停滞している場合True
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket or len(ticket["history"]) < 3:
            return False
        
        # 最新3件の出力を比較（最初の100文字）
        recent = [str(h.get("output", ""))[:100] for h in ticket["history"][-3:]]
        
        if len(set(recent)) == 1:
            ticket["status"]["stagnation_count"] += 1
            self.update_ticket(ticket_id, ticket)
            return True
        
        return False
    
    def should_stop(self, ticket_id: str) -> tuple[bool, Optional[str]]:
        """
        終了判定
        
        Args:
            ticket_id: チケットID
            
        Returns:
            (終了すべきか, 理由)
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return True, "Ticket not found"
        
        status = ticket["status"]
        
        # 1. 達成度が十分
        if status["confidence"] >= 0.9:
            return True, "Goal achieved (confidence >= 0.9)"
        
        # 2. 完了ステージ
        if status["stage"] == "done":
            return True, "Stage is 'done'"
        
        # 3. ターン上限
        if status["turn"] >= status["budget_turns"]:
            return True, f"Budget exhausted ({status['turn']}/{status['budget_turns']})"
        
        # 4. 停滞検知
        if status["stagnation_count"] >= 3:
            return True, f"Stagnation detected ({status['stagnation_count']} times)"
        
        # 5. 同じ役割が5回連続（クールダウン）
        if status["same_role_count"] >= 5:
            return True, f"Same role repeated {status['same_role_count']} times (cooldown)"
        
        return False, None
    
    def close_ticket(self, ticket_id: str, final_status: str = "completed") -> bool:
        """
        チケットクローズ
        
        Args:
            ticket_id: チケットID
            final_status: 最終ステータス（completed/failed/cancelled）
            
        Returns:
            成功したらTrue
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        ticket["final_status"] = final_status
        ticket["closed_at"] = datetime.now().isoformat()
        
        # アクティブリストから削除
        self.redis_client.srem("tickets:active", ticket_id)
        
        # クローズ済みリストに追加
        self.redis_client.sadd("tickets:closed", ticket_id)
        
        # 最終更新
        return self.update_ticket(ticket_id, ticket)
    
    def list_active_tickets(self) -> List[str]:
        """
        アクティブなチケット一覧
        
        Returns:
            チケットIDのリスト
        """
        return list(self.redis_client.smembers("tickets:active"))
    
    def get_summary(self, ticket_id: str) -> str:
        """
        チケットサマリー取得
        
        Args:
            ticket_id: チケットID
            
        Returns:
            サマリー文字列
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return "Ticket not found"
        
        status = ticket["status"]
        summary = f"""
🎫 Ticket: {ticket_id}
🎯 Goal: {ticket['goal']}
📊 Status: {status['stage']} (Turn {status['turn']}/{status['budget_turns']})
💯 Confidence: {status['confidence']:.2f}
📝 History: {len(ticket['history'])} entries
🎁 Artifacts: {len(ticket['artifacts'])} items
        """.strip()
        
        return summary


if __name__ == "__main__":
    # テスト
    tm = TicketManager()
    
    # チケット作成
    ticket_id = tm.create_ticket(
        goal="TODOアプリを作成",
        context=["Python", "Flask", "SQLite"],
        budget_turns=10
    )
    
    print(f"✅ Created: {ticket_id}")
    print(tm.get_summary(ticket_id))
    
    # 履歴追加
    tm.add_history(ticket_id, "remi", "plan", {"steps": ["環境構築", "実装", "テスト"]})
    tm.update_status(ticket_id, stage="plan", confidence=0.7)
    
    print("\n" + tm.get_summary(ticket_id))
    
    # 終了判定
    should_stop, reason = tm.should_stop(ticket_id)
    print(f"\nShould stop? {should_stop} ({reason})")



