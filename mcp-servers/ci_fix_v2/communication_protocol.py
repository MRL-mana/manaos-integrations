#!/usr/bin/env python3
"""
Communication Protocol — マルチエージェント通信プロトコル
=========================================================
複数の RL コンポーネント / エージェント間でメッセージングを行い、
知識共有・協調学習を実現する。

Princeton RL-Anything Round 10 Module 3.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


# ═══════════════════════════════════════════════════════
# 定数
# ═══════════════════════════════════════════════════════
MAX_MESSAGES = 5000
MAX_HISTORY = 200
BROADCAST_CHANNEL = "__broadcast__"


# ═══════════════════════════════════════════════════════
# メッセージ型
# ═══════════════════════════════════════════════════════
@dataclass
class Message:
    """通信メッセージ"""
    msg_id: str
    sender: str
    receiver: str  # "__broadcast__" for broadcast
    channel: str
    msg_type: str  # "knowledge", "request", "response", "event", "sync"
    payload: Dict[str, Any]
    timestamp: float = 0.0
    ttl: int = 10  # 生存サイクル数
    priority: int = 0  # 0=通常, 1=高, 2=緊急
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentInfo:
    """登録エージェント情報"""
    agent_id: str
    agent_type: str  # module name
    capabilities: List[str] = field(default_factory=list)
    subscriptions: Set[str] = field(default_factory=set)
    registered_at: float = 0.0
    last_active: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subscriptions"] = list(self.subscriptions)
        return d


@dataclass
class ChannelStats:
    """チャンネル統計"""
    channel: str
    message_count: int = 0
    subscriber_count: int = 0
    last_activity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════
# メインクラス
# ═══════════════════════════════════════════════════════
class CommunicationProtocol:
    """
    RLAnything コンポーネント間の通信ハブ。
    - エージェント（コンポーネント）の登録
    - チャンネルベースの Pub/Sub
    - ブロードキャスト / ダイレクトメッセージ
    - メッセージキュー / 履歴管理
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._persist_path = persist_path

        # エージェント登録
        self._agents: Dict[str, AgentInfo] = {}

        # チャンネル → 購読エージェントID
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)

        # エージェントID → 受信キュー
        self._queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_MESSAGES))

        # メッセージ履歴 (全体)
        self._history: deque = deque(maxlen=MAX_HISTORY)

        # 統計
        self._total_sent = 0
        self._total_broadcast = 0
        self._total_acknowledged = 0
        self._channel_counts: Dict[str, int] = defaultdict(int)

        # コールバック
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)

        self._restore()

    # ═══════════════════════════════════════════════════════
    # エージェント管理
    # ═══════════════════════════════════════════════════════
    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Optional[List[str]] = None,
    ) -> AgentInfo:
        """エージェントを通信ネットワークに登録"""
        now = time.time()
        info = AgentInfo(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or [],
            registered_at=now,
            last_active=now,
        )
        self._agents[agent_id] = info
        self._persist()
        return info

    def subscribe(self, agent_id: str, channel: str) -> bool:
        """チャンネルを購読"""
        if agent_id not in self._agents:
            return False
        self._subscriptions[channel].add(agent_id)
        self._agents[agent_id].subscriptions.add(channel)
        self._persist()
        return True

    def unsubscribe(self, agent_id: str, channel: str) -> bool:
        """チャンネル購読解除"""
        if agent_id not in self._agents:
            return False
        self._subscriptions[channel].discard(agent_id)
        self._agents[agent_id].subscriptions.discard(channel)
        return True

    def get_agents(self) -> Dict[str, Dict[str, Any]]:
        """全登録エージェント情報"""
        return {aid: a.to_dict() for aid, a in self._agents.items()}

    # ═══════════════════════════════════════════════════════
    # メッセージング
    # ═══════════════════════════════════════════════════════
    def send(
        self,
        sender: str,
        receiver: str,
        channel: str,
        msg_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        ttl: int = 10,
    ) -> Message:
        """ダイレクトメッセージ送信"""
        msg = self._create_message(sender, receiver, channel, msg_type, payload, priority, ttl)

        # 受信キューに追加
        if receiver in self._queues or receiver in self._agents:
            self._queues[receiver].append(msg)
            if receiver in self._agents:
                self._agents[receiver].messages_received += 1

        if sender in self._agents:
            self._agents[sender].messages_sent += 1
            self._agents[sender].last_active = time.time()

        self._total_sent += 1
        self._channel_counts[channel] += 1
        self._history.append(msg.to_dict())

        # コールバック実行
        self._fire_handlers(channel, msg)
        self._persist()
        return msg

    def broadcast(
        self,
        sender: str,
        channel: str,
        msg_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        ttl: int = 10,
    ) -> Message:
        """チャンネルにブロードキャスト"""
        msg = self._create_message(
            sender, BROADCAST_CHANNEL, channel, msg_type, payload, priority, ttl
        )

        # チャンネル購読者全員に配信
        subscribers = self._subscriptions.get(channel, set())
        for agent_id in subscribers:
            if agent_id != sender:
                self._queues[agent_id].append(msg)
                if agent_id in self._agents:
                    self._agents[agent_id].messages_received += 1

        if sender in self._agents:
            self._agents[sender].messages_sent += 1
            self._agents[sender].last_active = time.time()

        self._total_sent += 1
        self._total_broadcast += 1
        self._channel_counts[channel] += 1
        self._history.append(msg.to_dict())

        self._fire_handlers(channel, msg)
        self._persist()
        return msg

    def receive(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """エージェントの受信キューからメッセージ取得"""
        if agent_id not in self._queues:
            return []
        msgs = []
        count = 0
        while self._queues[agent_id] and count < limit:
            msg = self._queues[agent_id].popleft()
            msgs.append(msg.to_dict() if isinstance(msg, Message) else msg)
            count += 1
        return msgs

    def acknowledge(self, msg_id: str) -> bool:
        """メッセージを確認済みにマーク"""
        for item in self._history:
            if isinstance(item, dict) and item.get("msg_id") == msg_id:
                item["acknowledged"] = True
                self._total_acknowledged += 1
                return True
        return False

    # ═══════════════════════════════════════════════════════
    # 知識共有
    # ═══════════════════════════════════════════════════════
    def share_knowledge(
        self,
        sender: str,
        knowledge_type: str,
        data: Dict[str, Any],
    ) -> Message:
        """
        知識をブロードキャスト。
        knowledge_type: "policy_update", "reward_signal", "state_info", "anomaly_alert" 等
        """
        return self.broadcast(
            sender=sender,
            channel=f"knowledge.{knowledge_type}",
            msg_type="knowledge",
            payload={"knowledge_type": knowledge_type, "data": data},
            priority=1,
        )

    def request_knowledge(
        self,
        requester: str,
        target: str,
        knowledge_type: str,
        query: Dict[str, Any],
    ) -> Message:
        """特定エージェントに知識を要求"""
        return self.send(
            sender=requester,
            receiver=target,
            channel=f"knowledge.{knowledge_type}",
            msg_type="request",
            payload={"knowledge_type": knowledge_type, "query": query},
        )

    # ═══════════════════════════════════════════════════════
    # ハンドラ
    # ═══════════════════════════════════════════════════════
    def on_message(self, channel: str, handler: Callable[[Message], None]) -> None:
        """チャンネルにメッセージハンドラを登録"""
        self._handlers[channel].append(handler)

    def _fire_handlers(self, channel: str, msg: Message) -> None:
        for h in self._handlers.get(channel, []):
            try:
                h(msg)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """通信統計"""
        return {
            "total_sent": self._total_sent,
            "total_broadcast": self._total_broadcast,
            "total_acknowledged": self._total_acknowledged,
            "registered_agents": len(self._agents),
            "active_channels": len(self._channel_counts),
            "queue_sizes": {aid: len(q) for aid, q in self._queues.items() if len(q) > 0},
            "channel_counts": dict(self._channel_counts),
        }

    def get_channel_stats(self) -> List[Dict[str, Any]]:
        """チャンネル別統計"""
        result = []
        for ch, count in sorted(self._channel_counts.items(), key=lambda x: -x[1]):
            result.append(ChannelStats(
                channel=ch,
                message_count=count,
                subscriber_count=len(self._subscriptions.get(ch, set())),
            ).to_dict())
        return result

    def get_message_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """メッセージ履歴"""
        items = list(self._history)
        return items[-limit:]

    # ═══════════════════════════════════════════════════════
    # 内部
    # ═══════════════════════════════════════════════════════
    def _create_message(
        self,
        sender: str,
        receiver: str,
        channel: str,
        msg_type: str,
        payload: Dict[str, Any],
        priority: int,
        ttl: int,
    ) -> Message:
        raw = f"{sender}:{receiver}:{channel}:{time.time()}"
        msg_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return Message(
            msg_id=msg_id,
            sender=sender,
            receiver=receiver,
            channel=channel,
            msg_type=msg_type,
            payload=payload,
            timestamp=time.time(),
            ttl=ttl,
            priority=priority,
        )

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "agents": {aid: a.to_dict() for aid, a in self._agents.items()},
                "subscriptions": {ch: list(subs) for ch, subs in self._subscriptions.items()},
                "total_sent": self._total_sent,
                "total_broadcast": self._total_broadcast,
                "total_acknowledged": self._total_acknowledged,
                "channel_counts": dict(self._channel_counts),
                "history": list(self._history)[-MAX_HISTORY:],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            # エージェント復元
            for aid, adict in data.get("agents", {}).items():
                subs = set(adict.pop("subscriptions", []))
                info = AgentInfo(**{k: v for k, v in adict.items() if k != "subscriptions"})
                info.subscriptions = subs
                self._agents[aid] = info
            # 購読復元
            for ch, subs_list in data.get("subscriptions", {}).items():
                self._subscriptions[ch] = set(subs_list)
            self._total_sent = data.get("total_sent", 0)
            self._total_broadcast = data.get("total_broadcast", 0)
            self._total_acknowledged = data.get("total_acknowledged", 0)
            self._channel_counts = defaultdict(int, data.get("channel_counts", {}))
            for item in data.get("history", []):
                self._history.append(item)
        except Exception:
            pass
