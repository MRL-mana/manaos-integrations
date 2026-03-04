#!/usr/bin/env python3
"""
🧠 Enhanced Conversation Context
会話の流れを理解する強化版コンテキストシステム

機能:
- 短期・中期・長期記憶の3層構造
- 指示語解決（「それ」「あれ」など）
- トピック継続性判定
- 文脈補完
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedConversationContext:
    """強化版会話コンテキスト"""
    
    def __init__(self):
        # 短期記憶（直近の会話）
        self.short_term = []  # 直近10ターン
        self.short_term_limit = 10
        
        # 中期記憶（今日の会話サマリー）
        self.mid_term = {
            'topics': [],               # 今日話したトピック
            'decisions': [],            # 今日の決定事項
            'tasks_created': [],        # 作成したタスク
            'mood_progression': [],     # 感情の変化
            'key_phrases': []           # キーフレーズ
        }
        
        # 長期記憶への参照（AI Learning Systemから取得）
        self.long_term_memories = []
        
        # 会話の流れ把握
        self.conversation_flow = {
            'current_topic': None,          # 現在のトピック
            'related_topics': [],           # 関連トピック
            'pending_questions': [],        # 保留中の質問
            'unresolved_issues': [],        # 未解決の問題
            'last_mentioned_entities': {}   # 最後に言及されたエンティティ
        }
        
        # 指示語マッピング
        self.reference_map = {
            'それ': None,
            'あれ': None,
            'これ': None,
            'その': None,
            'あの': None,
            'この': None
        }
        
        logger.info("🧠 Enhanced Conversation Context initialized")
    
    def add_turn(self, user_msg: str, bot_msg: str, intent: str = None, emotion: str = 'neutral'):
        """会話ターンを追加"""
        turn = {
            'user': user_msg,
            'bot': bot_msg,
            'intent': intent,
            'emotion': emotion,
            'timestamp': datetime.now().isoformat(),
            'extracted_entities': self._extract_entities(user_msg)
        }
        
        # 短期記憶に追加
        self.short_term.append(turn)
        
        # 古い履歴を削除
        if len(self.short_term) > self.short_term_limit:
            self.short_term = self.short_term[-self.short_term_limit:]
        
        # 中期記憶を更新
        self._update_mid_term(turn)
        
        # 会話フローを更新
        self._update_conversation_flow(turn)
        
        # 指示語マッピングを更新
        self._update_reference_map(turn)
        
        logger.info(f"  ✅ Added turn - Topic: {self.conversation_flow['current_topic']}")
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """エンティティを抽出（簡易版）"""
        entities = {
            'tasks': [],
            'dates': [],
            'names': [],
            'objects': []
        }
        
        # タスク系キーワード
        task_keywords = ['タスク', '仕事', '作業', 'やること', 'TODO']
        for keyword in task_keywords:
            if keyword in text:
                # 簡易的にキーワード後の文字列を抽出
                entities['tasks'].append(keyword)
        
        # 日時系キーワード
        date_keywords = ['今日', '明日', '昨日', '来週', '先週', '今週']
        for keyword in date_keywords:
            if keyword in text:
                entities['dates'].append(keyword)
        
        # オブジェクト（名詞っぽいもの）
        # 簡易的に長めの単語を抽出
        words = text.split()
        for word in words:
            if len(word) > 3 and word not in ['について', 'だから', 'けれど']:
                entities['objects'].append(word)
        
        return entities
    
    def _update_mid_term(self, turn: Dict[str, Any]):
        """中期記憶を更新"""
        user_msg = turn['user']
        
        # トピック抽出
        if turn.get('intent'):
            topic = turn['intent']
            if topic not in self.mid_term['topics']:
                self.mid_term['topics'].append(topic)
        
        # 決定事項
        decision_keywords = ['決めた', '決定', 'することにした', 'やる', '実行する']
        if any(kw in user_msg for kw in decision_keywords):
            self.mid_term['decisions'].append({
                'decision': user_msg,
                'timestamp': turn['timestamp']
            })
        
        # タスク作成
        if 'タスク' in user_msg and ('追加' in user_msg or '作成' in user_msg):
            self.mid_term['tasks_created'].append({
                'task': user_msg,
                'timestamp': turn['timestamp']
            })
        
        # 感情の変化
        emotion = turn.get('emotion', 'neutral')
        self.mid_term['mood_progression'].append({
            'emotion': emotion,
            'timestamp': turn['timestamp']
        })
        
        # キーフレーズ（長めの文を記録）
        if len(user_msg) > 10:
            self.mid_term['key_phrases'].append(user_msg[:50])
            # 最新50件のみ保持
            self.mid_term['key_phrases'] = self.mid_term['key_phrases'][-50:]
    
    def _update_conversation_flow(self, turn: Dict[str, Any]):
        """会話フローを更新"""
        user_msg = turn['user']
        entities = turn['extracted_entities']
        
        # 現在のトピックを更新
        if turn.get('intent'):
            self.conversation_flow['current_topic'] = turn['intent']
        elif entities['objects']:
            # エンティティからトピックを推定
            self.conversation_flow['current_topic'] = entities['objects'][0]
        
        # 質問文を検出
        if '？' in user_msg or '?' in user_msg:
            self.conversation_flow['pending_questions'].append({
                'question': user_msg,
                'timestamp': turn['timestamp']
            })
            # 最新5件のみ
            self.conversation_flow['pending_questions'] = \
                self.conversation_flow['pending_questions'][-5:]
        
        # 最後に言及されたエンティティを更新
        for entity_type, entity_list in entities.items():
            if entity_list:
                self.conversation_flow['last_mentioned_entities'][entity_type] = entity_list[-1]
    
    def _update_reference_map(self, turn: Dict[str, Any]):
        """指示語マッピングを更新"""
        user_msg = turn['user']
        entities = turn['extracted_entities']
        
        # 「それ」「あれ」などが出現したら、前のターンのオブジェクトを参照
        if any(ref in user_msg for ref in ['それ', 'あれ', 'これ']):
            if len(self.short_term) >= 2:
                prev_turn = self.short_term[-2]
                prev_entities = prev_turn.get('extracted_entities', {})
                
                if prev_entities.get('objects'):
                    self.reference_map['それ'] = prev_entities['objects'][0]
                    self.reference_map['あれ'] = prev_entities['objects'][0]
    
    def understand_context(self, new_message: str) -> Dict[str, Any]:
        """
        会話の流れを理解
        
        Returns:
            理解した文脈情報
        """
        logger.info(f"🔍 Understanding context for: {new_message[:50]}...")
        
        context = {
            'message': new_message,
            'resolved_references': {},      # 解決された指示語
            'related_previous_turns': [],   # 関連する過去ターン
            'current_topic': self.conversation_flow['current_topic'],
            'is_topic_continuation': False, # トピック継続か
            'is_followup_question': False,  # フォローアップ質問か
            'missing_context': []           # 不足している文脈
        }
        
        # 1. 指示語を解決
        context['resolved_references'] = self._resolve_references(new_message)
        
        # 2. トピックの継続性を判定
        context['is_topic_continuation'] = self._is_topic_continued(new_message)
        
        # 3. フォローアップ質問かを判定
        context['is_followup_question'] = self._is_followup(new_message)
        
        # 4. 関連する過去ターンを検索
        context['related_previous_turns'] = self._find_related_turns(new_message)
        
        # 5. 不足している文脈を特定
        context['missing_context'] = self._identify_missing_context(new_message, context)
        
        logger.info(f"  ✅ Context understood - Topic: {context['current_topic']}")
        
        return context
    
    def _resolve_references(self, message: str) -> Dict[str, str]:
        """指示語を解決"""
        resolved = {}
        
        for ref_word, ref_target in self.reference_map.items():
            if ref_word in message and ref_target:
                resolved[ref_word] = ref_target
        
        return resolved
    
    def _is_topic_continued(self, message: str) -> bool:
        """トピックが継続しているか判定"""
        if not self.conversation_flow['current_topic']:
            return False
        
        current_topic = self.conversation_flow['current_topic']
        
        # 現在のトピックが言及されているか
        if current_topic in message:
            return True
        
        # 指示語が使われているか（トピック継続の可能性）
        if any(ref in message for ref in ['それ', 'あれ', 'その', 'あの']):
            return True
        
        # 短いメッセージ（フォローアップの可能性）
        if len(message) < 15:
            return True
        
        return False
    
    def _is_followup(self, message: str) -> bool:
        """フォローアップ質問か判定"""
        followup_keywords = [
            'もっと', 'さらに', '詳しく', '具体的に', '他に',
            'それで', 'で、', 'じゃあ', 'なら'
        ]
        
        return any(kw in message for kw in followup_keywords)
    
    def _find_related_turns(self, message: str, limit: int = 3) -> List[Dict]:
        """関連する過去ターンを検索"""
        related = []
        
        # 簡易的にキーワードマッチング
        message_lower = message.lower()
        
        for turn in reversed(self.short_term[-5:]):  # 直近5ターン
            user_msg = turn['user'].lower()
            
            # 共通の単語がある
            message_words = set(message_lower.split())
            turn_words = set(user_msg.split())
            
            common_words = message_words & turn_words
            
            if len(common_words) > 2:  # 3単語以上共通
                related.append({
                    'turn': turn,
                    'relevance': len(common_words)
                })
        
        # 関連度でソート
        related = sorted(related, key=lambda x: x['relevance'], reverse=True)
        
        return related[:limit]
    
    def _identify_missing_context(self, message: str, context: Dict) -> List[str]:
        """不足している文脈を特定"""
        missing = []
        
        # 指示語が解決できない
        unresolved_refs = [
            ref for ref in ['それ', 'あれ', 'これ']
            if ref in message and ref not in context['resolved_references']
        ]
        
        if unresolved_refs:
            missing.append(f"指示語が不明: {', '.join(unresolved_refs)}")
        
        # 主語が省略されている可能性
        if len(message) < 10 and not context['is_topic_continuation']:
            missing.append("主語が省略されている可能性")
        
        return missing
    
    def get_context_summary(self, format: str = 'text') -> str:
        """コンテキスト要約"""
        if not self.short_term:
            return "会話履歴なし"
        
        if format == 'text':
            summary = "\n【直近の会話】\n"
            
            for turn in self.short_term[-3:]:  # 直近3ターン
                summary += f"Mana: {turn['user'][:50]}...\n"
                summary += f"Trinity: {turn['bot'][:50]}...\n"
            
            if self.conversation_flow['current_topic']:
                summary += f"\n【現在のトピック】{self.conversation_flow['current_topic']}\n"
            
            return summary
        
        elif format == 'json':
            return {
                'short_term_count': len(self.short_term),
                'current_topic': self.conversation_flow['current_topic'],
                'topics_discussed': self.mid_term['topics'],
                'mood': self.mid_term['mood_progression'][-1] if self.mid_term['mood_progression'] else None,
                'pending_questions': len(self.conversation_flow['pending_questions'])
            }
    
    def should_ask_followup(self) -> bool:
        """フォローアップ質問すべきか判定"""
        if len(self.short_term) < 2:
            return False
        
        last_turn = self.short_term[-1]
        
        # 最後の応答が質問で終わっていない
        last_bot = last_turn['bot']
        if not (last_bot.endswith('？') or last_bot.endswith('?')):
            # かつ、会話が途切れそう
            if len(last_turn['user']) < 15:
                return True
        
        return False
    
    def reset_daily(self):
        """日次リセット（中期記憶をクリア）"""
        self.mid_term = {
            'topics': [],
            'decisions': [],
            'tasks_created': [],
            'mood_progression': [],
            'key_phrases': []
        }
        logger.info("  🔄 Mid-term memory reset for new day")


# テスト用
def test_context():
    """コンテキストシステムのテスト"""
    context = EnhancedConversationContext()
    
    print("\n" + "="*60)
    print("Enhanced Conversation Context - Test")
    print("="*60)
    
    # テスト会話
    context.add_turn(
        "プロジェクトのプレゼン準備してる",
        "頑張ってください！スライドの構成は決まりましたか？",
        intent="task_management",
        emotion="neutral"
    )
    
    context.add_turn(
        "まだ決まってない。アイデアある？",
        "まず目標を明確にしましょう。何を伝えたいですか？",
        intent="brainstorming",
        emotion="worried"
    )
    
    context.add_turn(
        "それについてもっと詳しく教えて",
        "プレゼンの目標設定には3つのポイントがあります...",
        intent="explanation",
        emotion="neutral"
    )
    
    # コンテキスト理解テスト
    print("\n🔍 Understanding new message:")
    new_msg = "それについてもっと詳しく教えて"
    understanding = context.understand_context(new_msg)
    
    print(f"  Message: {new_msg}")
    print(f"  Current topic: {understanding['current_topic']}")
    print(f"  Is continuation: {understanding['is_topic_continuation']}")
    print(f"  Is followup: {understanding['is_followup_question']}")
    print(f"  Resolved references: {understanding['resolved_references']}")
    
    # サマリーテスト
    print("\n📝 Context summary:")
    print(context.get_context_summary())


if __name__ == '__main__':
    test_context()



