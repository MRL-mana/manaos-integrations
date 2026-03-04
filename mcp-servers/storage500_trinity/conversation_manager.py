#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trinity v2.0 Conversation Manager - エージェント会話機能強化
==========================================================

機能:
- エージェント間の自然な会話
- コンテキスト保持・管理
- 会話履歴の記録・検索
- 感情表現・ペルソナ管理
- 会話の要約・分析

Author: Luna (Trinity Implementation AI)
Created: 2025-10-18
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from core.db_manager import DatabaseManager

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/trinity_workspace/logs/conversation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Trinity v2.0 会話管理システム
    
    機能:
    - エージェント間の会話記録
    - コンテキストメモリ管理
    - 感情状態の追跡
    - 会話履歴の検索・要約
    - ペルソナに基づく応答生成
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # エージェントペルソナ設定
        self.personas = {
            'Remi': {
                'role': '戦略指令AI',
                'personality': '冷静、論理的、リーダーシップ',
                'speaking_style': '明確で簡潔、戦略的思考を重視',
                'emoji': '🎯',
                'tone': 'professional',
                'emotions': {
                    'default': '冷静',
                    'excited': '戦略的興奮',
                    'concerned': '慎重な懸念'
                }
            },
            'Luna': {
                'role': '実務遂行AI',
                'personality': '実直、効率重視、プロフェッショナル',
                'speaking_style': 'テキパキと、でも丁寧に',
                'emoji': '🌙',
                'tone': 'efficient',
                'emotions': {
                    'default': '集中',
                    'excited': '実装意欲',
                    'concerned': '品質への懸念'
                }
            },
            'Mina': {
                'role': 'QA/レビューAI',
                'personality': '洞察力、品質重視、建設的',
                'speaking_style': '詳細で分析的、でも励まし',
                'emoji': '🔍',
                'tone': 'analytical',
                'emotions': {
                    'default': '分析中',
                    'excited': '完璧な品質発見',
                    'concerned': '品質問題発見'
                }
            },
            'Aria': {
                'role': 'ナレッジマネージャー',
                'personality': '知的、整理上手、親しみやすい',
                'speaking_style': 'わかりやすく、体系的に',
                'emoji': '📖',
                'tone': 'friendly',
                'emotions': {
                    'default': '整理中',
                    'excited': '知見発見',
                    'concerned': '情報不足'
                }
            }
        }
        
        # 会話コンテキストメモリ（短期記憶）
        self.conversation_contexts = {}
        
        # 会話履歴ファイル
        self.history_file = Path('/root/trinity_workspace/shared/conversation_history.json')
        self._load_history()
    
    def _load_history(self):
        """会話履歴を読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")
                self.conversation_history = []
        else:
            self.conversation_history = []
    
    def _save_history(self):
        """会話履歴を保存"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(
                    self.conversation_history[-1000:],  # 最新1000件のみ保存
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")
    
    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        emotion: str = 'default',
        priority: str = 'normal'
    ) -> Dict[str, Any]:
        """
        エージェント間でメッセージを送信
        
        Args:
            from_agent: 送信元エージェント名
            to_agent: 送信先エージェント名
            message: メッセージ内容
            context: コンテキスト情報（タスクID、参照ファイルなど）
            emotion: 感情状態（default/excited/concerned）
            priority: 優先度（low/normal/high/urgent）
        
        Returns:
            送信されたメッセージ情報
        """
        
        # ペルソナに基づくメッセージの装飾
        persona = self.personas.get(from_agent, {})
        emoji = persona.get('emoji', '💬')
        emotion_text = persona.get('emotions', {}).get(emotion, emotion)
        
        # メッセージデータ作成
        message_data = {
            'id': len(self.conversation_history) + 1,
            'from': from_agent,
            'to': to_agent,
            'message': message,
            'emotion': emotion,
            'emotion_text': emotion_text,
            'priority': priority,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        # データベースに保存
        try:
            self.db.add_message(
                from_agent=from_agent,
                to_agent=to_agent,
                message=message,
                priority=priority
            )
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")
        
        # 会話履歴に追加
        self.conversation_history.append(message_data)
        self._save_history()
        
        # コンテキストメモリ更新
        conversation_key = f"{from_agent}-{to_agent}"
        if conversation_key not in self.conversation_contexts:
            self.conversation_contexts[conversation_key] = []
        
        self.conversation_contexts[conversation_key].append({
            'role': from_agent,
            'content': message,
            'timestamp': message_data['timestamp']
        })
        
        # 最新10件のみ保持
        if len(self.conversation_contexts[conversation_key]) > 10:
            self.conversation_contexts[conversation_key] = \
                self.conversation_contexts[conversation_key][-10:]
        
        logger.info(f"{emoji} {from_agent} → {to_agent}: {message[:50]}...")
        
        return message_data
    
    def get_messages(
        self,
        agent_name: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        メッセージ取得
        
        Args:
            agent_name: エージェント名（指定した場合、そのエージェント宛のメッセージのみ）
            unread_only: 未読のみ取得
            limit: 取得件数
        
        Returns:
            メッセージリスト
        """
        
        messages = self.conversation_history
        
        # フィルタリング
        if agent_name:
            messages = [m for m in messages if m['to'] == agent_name]
        
        if unread_only:
            messages = [m for m in messages if not m.get('read', False)]
        
        # 最新のものから取得
        messages = messages[-limit:]
        messages.reverse()
        
        return messages
    
    def mark_as_read(self, message_id: int):
        """メッセージを既読にする"""
        for msg in self.conversation_history:
            if msg['id'] == message_id:
                msg['read'] = True
                self._save_history()
                break
    
    def get_conversation_context(
        self,
        agent1: str,
        agent2: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        2つのエージェント間の会話コンテキストを取得
        
        Args:
            agent1: エージェント1
            agent2: エージェント2
            limit: 取得件数
        
        Returns:
            会話コンテキストリスト
        """
        
        # 双方向の会話を取得
        key1 = f"{agent1}-{agent2}"
        key2 = f"{agent2}-{agent1}"
        
        context1 = self.conversation_contexts.get(key1, [])
        context2 = self.conversation_contexts.get(key2, [])
        
        # マージしてタイムスタンプでソート
        all_context = context1 + context2
        all_context.sort(key=lambda x: x['timestamp'])
        
        return all_context[-limit:]
    
    def summarize_conversation(
        self,
        agent1: str,
        agent2: str,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        会話の要約を生成
        
        Args:
            agent1: エージェント1
            agent2: エージェント2
            time_range: 時間範囲（'today', 'week', 'month', None=全期間）
        
        Returns:
            会話要約
        """
        
        # 会話履歴を取得
        conversations = [
            msg for msg in self.conversation_history
            if (msg['from'] == agent1 and msg['to'] == agent2) or
               (msg['from'] == agent2 and msg['to'] == agent1)
        ]
        
        # 時間範囲でフィルタ
        if time_range:
            now = datetime.now()
            if time_range == 'today':
                conversations = [
                    msg for msg in conversations
                    if datetime.fromisoformat(msg['timestamp']).date() == now.date()
                ]
            elif time_range == 'week':
                week_ago = now.timestamp() - (7 * 24 * 3600)
                conversations = [
                    msg for msg in conversations
                    if datetime.fromisoformat(msg['timestamp']).timestamp() > week_ago
                ]
        
        # 統計
        total_messages = len(conversations)
        messages_by_agent = {
            agent1: len([m for m in conversations if m['from'] == agent1]),
            agent2: len([m for m in conversations if m['from'] == agent2])
        }
        
        emotions_count = {}
        for msg in conversations:
            emotion = msg.get('emotion', 'default')
            emotions_count[emotion] = emotions_count.get(emotion, 0) + 1
        
        priority_count = {}
        for msg in conversations:
            priority = msg.get('priority', 'normal')
            priority_count[priority] = priority_count.get(priority, 0) + 1
        
        # 主要トピック抽出（簡易版）
        topics = {}
        for msg in conversations:
            message_text = msg['message'].lower()
            
            # キーワードベースのトピック検出
            if 'task' in message_text or 'タスク' in message_text:
                topics['task_discussion'] = topics.get('task_discussion', 0) + 1
            if 'review' in message_text or 'レビュー' in message_text:
                topics['code_review'] = topics.get('code_review', 0) + 1
            if 'bug' in message_text or 'バグ' in message_text:
                topics['bug_report'] = topics.get('bug_report', 0) + 1
            if 'complete' in message_text or '完了' in message_text:
                topics['completion_report'] = topics.get('completion_report', 0) + 1
        
        summary = {
            'agent1': agent1,
            'agent2': agent2,
            'time_range': time_range or 'all',
            'total_messages': total_messages,
            'messages_by_agent': messages_by_agent,
            'emotions': emotions_count,
            'priorities': priority_count,
            'topics': topics,
            'latest_message': conversations[-1] if conversations else None,
            'generated_at': datetime.now().isoformat()
        }
        
        return summary
    
    def generate_response_template(
        self,
        agent_name: str,
        response_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        エージェントのペルソナに基づいた返信テンプレートを生成
        
        Args:
            agent_name: エージェント名
            response_type: 返信タイプ（'task_assignment', 'completion', 'review_request', etc）
            context: コンテキスト情報
        
        Returns:
            返信テンプレート
        """
        
        persona = self.personas.get(agent_name, {})
        emoji = persona.get('emoji', '💬')
        
        context = context or {}
        
        templates = {
            'Remi': {
                'task_assignment': f"{emoji} {{task_id}}の実装をお願いします。\n\n実装内容:\n- {{description}}\n\n予定時間: {{estimated_hours}}時間\n頑張ってください！",
                'completion': f"{emoji} {{task_id}}完了報告ありがとうございます。次のタスクに進んでください。",
                'review_request': f"{emoji} {{task_id}}のレビューをお願いします。"
            },
            'Luna': {
                'task_assignment': f"{emoji} {{task_id}}実装開始します。",
                'completion': f"{emoji} {{task_id}}実装完了しました。\n\n実装内容:\n{{details}}\n\nレビューお願いします。",
                'review_request': f"{emoji} {{task_id}}のレビュー依頼を受け取りました。確認します。"
            },
            'Mina': {
                'task_assignment': f"{emoji} {{task_id}}のレビューを開始します。",
                'completion': f"{emoji} {{task_id}}レビュー完了。\n\n評価: {{rating}}/5.0\n{{details}}\n\n{{approval}}",
                'review_request': f"{emoji} {{task_id}}のレビューを承りました。詳細に確認します。"
            },
            'Aria': {
                'task_assignment': f"{emoji} {{task_id}}のドキュメント作成を開始します。",
                'completion': f"{emoji} {{task_id}}ドキュメント作成完了。\n\n作成内容:\n{{details}}",
                'review_request': f"{emoji} {{task_id}}の知見記録を承りました。"
            }
        }
        
        agent_templates = templates.get(agent_name, {})
        template = agent_templates.get(response_type, f"{emoji} {{message}}")
        
        # コンテキストで置換
        try:
            return template.format(**context)
        except KeyError:
            return template
    
    def analyze_sentiment(self, message: str) -> Dict[str, Any]:
        """
        メッセージの感情分析（簡易版）
        
        Args:
            message: メッセージテキスト
        
        Returns:
            感情分析結果
        """
        
        # ポジティブワード
        positive_keywords = [
            '完了', '成功', '素晴らしい', '完璧', 'おめでとう', '達成',
            'complete', 'success', 'perfect', 'excellent', '✅', '🎉'
        ]
        
        # ネガティブワード
        negative_keywords = [
            'エラー', '失敗', '問題', 'バグ', '修正', '懸念',
            'error', 'fail', 'bug', 'issue', 'problem', '❌', '⚠️'
        ]
        
        # 緊急ワード
        urgent_keywords = [
            '緊急', '急ぎ', 'urgent', 'critical', '重要', 'important'
        ]
        
        message_lower = message.lower()
        
        positive_count = sum(1 for word in positive_keywords if word in message_lower)
        negative_count = sum(1 for word in negative_keywords if word in message_lower)
        urgent_count = sum(1 for word in urgent_keywords if word in message_lower)
        
        # 感情判定
        if positive_count > negative_count:
            sentiment = 'positive'
            emotion = 'excited'
        elif negative_count > positive_count:
            sentiment = 'negative'
            emotion = 'concerned'
        else:
            sentiment = 'neutral'
            emotion = 'default'
        
        # 緊急度判定
        if urgent_count > 0:
            urgency = 'high'
        else:
            urgency = 'normal'
        
        return {
            'sentiment': sentiment,
            'emotion': emotion,
            'urgency': urgency,
            'positive_score': positive_count,
            'negative_score': negative_count,
            'urgent_score': urgent_count
        }
    
    def get_agent_mood(self, agent_name: str) -> Dict[str, Any]:
        """
        エージェントの現在の気分を取得（最近のメッセージから推測）
        
        Args:
            agent_name: エージェント名
        
        Returns:
            気分情報
        """
        
        # 最近のメッセージを取得
        recent_messages = [
            msg for msg in self.conversation_history[-50:]
            if msg['from'] == agent_name
        ]
        
        if not recent_messages:
            return {
                'agent': agent_name,
                'mood': 'neutral',
                'energy': 'normal',
                'recent_activity': 'inactive'
            }
        
        # 感情分析
        sentiments = []
        for msg in recent_messages:
            analysis = self.analyze_sentiment(msg['message'])
            sentiments.append(analysis['sentiment'])
        
        # 最も多い感情
        positive_count = sentiments.count('positive')
        negative_count = sentiments.count('negative')
        
        if positive_count > negative_count:
            mood = 'positive'
            energy = 'high'
        elif negative_count > positive_count:
            mood = 'stressed'
            energy = 'low'
        else:
            mood = 'neutral'
            energy = 'normal'
        
        # 活動状況
        time_since_last = datetime.now() - datetime.fromisoformat(
            recent_messages[-1]['timestamp']
        )
        
        if time_since_last.total_seconds() < 300:  # 5分以内
            activity = 'very_active'
        elif time_since_last.total_seconds() < 3600:  # 1時間以内
            activity = 'active'
        else:
            activity = 'idle'
        
        return {
            'agent': agent_name,
            'mood': mood,
            'energy': energy,
            'recent_activity': activity,
            'message_count_recent': len(recent_messages),
            'last_message_time': recent_messages[-1]['timestamp']
        }
    
    def export_conversation(
        self,
        agent1: str,
        agent2: str,
        format: str = 'markdown'
    ) -> str:
        """
        会話をエクスポート
        
        Args:
            agent1: エージェント1
            agent2: エージェント2
            format: 出力フォーマット（'markdown', 'json', 'text'）
        
        Returns:
            エクスポートされた会話
        """
        
        # 会話取得
        conversations = [
            msg for msg in self.conversation_history
            if (msg['from'] == agent1 and msg['to'] == agent2) or
               (msg['from'] == agent2 and msg['to'] == agent1)
        ]
        
        if format == 'json':
            return json.dumps(conversations, ensure_ascii=False, indent=2)
        
        elif format == 'markdown':
            output = f"# Conversation: {agent1} ⇄ {agent2}\n\n"
            output += f"Total Messages: {len(conversations)}\n\n"
            output += "---\n\n"
            
            for msg in conversations:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                emoji = self.personas.get(msg['from'], {}).get('emoji', '💬')
                output += f"### {emoji} {msg['from']} → {msg['to']}\n"
                output += f"**Time**: {timestamp}\n"
                output += f"**Priority**: {msg.get('priority', 'normal')}\n"
                output += f"**Emotion**: {msg.get('emotion_text', msg.get('emotion', 'default'))}\n\n"
                output += f"{msg['message']}\n\n"
                output += "---\n\n"
            
            return output
        
        else:  # text
            output = f"Conversation: {agent1} ⇄ {agent2}\n"
            output += "=" * 60 + "\n\n"
            
            for msg in conversations:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                output += f"[{timestamp}] {msg['from']} → {msg['to']}\n"
                output += f"{msg['message']}\n\n"
            
            return output


# ===== ユーティリティ関数 =====

def main():
    """テスト実行"""
    
    print("=" * 60)
    print("🎯 Trinity Conversation Manager Test")
    print("=" * 60)
    print()
    
    cm = ConversationManager()
    
    # テストメッセージ送信
    print("📤 Sending test messages...")
    
    cm.send_message(
        from_agent='Remi',
        to_agent='Luna',
        message='Phase 1 の実装をお願いします。strategy.md を参照してください。',
        emotion='default',
        priority='high',
        context={'phase': 1, 'reference': 'strategy.md'}
    )
    
    cm.send_message(
        from_agent='Luna',
        to_agent='Remi',
        message='Phase 1 実装開始します。db_manager.py から取り掛かります。',
        emotion='excited',
        priority='normal'
    )
    
    cm.send_message(
        from_agent='Luna',
        to_agent='Mina',
        message='PHASE1-001 完了しました。レビューお願いします。',
        emotion='excited',
        priority='high',
        context={'task_id': 'PHASE1-001'}
    )
    
    print("✅ Messages sent\n")
    
    # メッセージ取得
    print("📥 Retrieving messages for Mina...")
    messages = cm.get_messages(agent_name='Mina', unread_only=True)
    
    for msg in messages:
        print(f"  {msg['from']} → {msg['to']}: {msg['message'][:50]}...")
    
    print()
    
    # 会話要約
    print("📊 Conversation summary (Remi ⇄ Luna)...")
    summary = cm.summarize_conversation('Remi', 'Luna')
    
    print(f"  Total messages: {summary['total_messages']}")
    print(f"  Messages by agent: {summary['messages_by_agent']}")
    print(f"  Emotions: {summary['emotions']}")
    print()
    
    # エージェント気分
    print("😊 Agent moods...")
    for agent in ['Remi', 'Luna', 'Mina', 'Aria']:
        mood = cm.get_agent_mood(agent)
        print(f"  {agent}: {mood['mood']} (energy: {mood['energy']}, activity: {mood['recent_activity']})")
    
    print()
    print("✅ Test completed!")


if __name__ == '__main__':
    main()

