#!/usr/bin/env python3
"""
Consciousness State Management - 意識状態管理システム

AIの「意識状態」を永続化し、再起動後も思考を継承します。

機能:
- 意識状態の保存・復元
- 思考プロセスの記録
- 対話文脈の連鎖保持
- 時系列記憶管理
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib


class ConsciousnessState:
    """意識状態管理"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "shared" / "memory"
        self.state_file = self.memory_dir / "consciousness_state.json"
        
        # データベース
        self.db_path = self.workspace / "shared" / "consciousness.db"
        self.init_database()
        
        # 現在の状態
        self.current_state = self.load_state()
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 思考履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thought_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                thought_type TEXT NOT NULL,
                content TEXT NOT NULL,
                context_id TEXT,
                parent_thought_id INTEGER,
                confidence REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (parent_thought_id) REFERENCES thought_history(id)
            )
        """)
        
        # 対話コンテキストテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dialogue_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_id TEXT NOT NULL UNIQUE,
                agent TEXT NOT NULL,
                topic TEXT,
                started_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                context_data TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # コンテキストチェーンテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_context_id TEXT NOT NULL,
                to_context_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (from_context_id) REFERENCES dialogue_context(context_id),
                FOREIGN KEY (to_context_id) REFERENCES dialogue_context(context_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def save_state(self, agent: str = "all"):
        """意識状態を保存"""
        if agent == "all":
            agents = ['remi', 'luna', 'mina', 'aria']
        else:
            agents = [agent]
        
        state = {
            'version': '1.0.0',
            'saved_at': datetime.now().isoformat(),
            'agents': {}
        }
        
        for ag in agents:
            agent_state = self._capture_agent_state(ag)
            state['agents'][ag] = agent_state
        
        # ファイルに保存
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        self.current_state = state
        
        print(f"💾 Consciousness state saved: {len(agents)} agent(s)")
        return state
        
    def load_state(self) -> Dict:
        """意識状態を読み込み"""
        if not self.state_file.exists():
            return self._create_default_state()
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            print(f"🧠 Consciousness state loaded from {state['saved_at']}")
            return state
        except Exception as e:
            print(f"⚠️  Failed to load state: {e}")
            return self._create_default_state()
        
    def _create_default_state(self) -> Dict:
        """デフォルト状態を作成"""
        return {
            'version': '1.0.0',
            'saved_at': datetime.now().isoformat(),
            'agents': {
                'remi': self._create_agent_default('remi'),
                'luna': self._create_agent_default('luna'),
                'mina': self._create_agent_default('mina'),
                'aria': self._create_agent_default('aria')
            }
        }
        
    def _create_agent_default(self, agent: str) -> Dict:
        """エージェントのデフォルト状態"""
        return {
            'agent': agent,
            'active_since': datetime.now().isoformat(),
            'current_context': None,
            'recent_thoughts': [],
            'emotional_state': {
                'confidence': 0.5,
                'enthusiasm': 0.5,
                'focus': 0.5
            },
            'working_memory': {}
        }
        
    def _capture_agent_state(self, agent: str) -> Dict:
        """エージェントの現在状態をキャプチャ"""
        # 最近の思考を取得
        recent_thoughts = self.get_recent_thoughts(agent, limit=10)
        
        # アクティブなコンテキストを取得
        active_context = self.get_active_context(agent)
        
        return {
            'agent': agent,
            'active_since': datetime.now().isoformat(),
            'current_context': active_context,
            'recent_thoughts': recent_thoughts,
            'emotional_state': self._get_emotional_state(agent),
            'working_memory': self._get_working_memory(agent)
        }
        
    def _get_working_memory(self, agent: str) -> Dict:
        """作業メモリを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近のアクティブコンテキストを取得
        cursor.execute("""
            SELECT context_id, topic, message_count
            FROM dialogue_context
            WHERE agent = ? AND status = 'active'
            ORDER BY last_updated DESC
            LIMIT 3
        """, (agent,))
        
        active_contexts = []
        for row in cursor.fetchall():
            active_contexts.append({
                'context_id': row[0],
                'topic': row[1],
                'message_count': row[2]
            })
        
        # 最近の思考のキーワード抽出
        recent_thoughts = self.get_recent_thoughts(agent, limit=5)
        focus_keywords = self._extract_keywords(recent_thoughts)
        
        conn.close()
        
        return {
            'active_contexts': active_contexts,
            'focus_keywords': focus_keywords,
            'context_count': len(active_contexts),
            'last_updated': datetime.now().isoformat()
        }
        
    def _extract_keywords(self, thoughts: List[Dict]) -> List[str]:
        """思考からキーワードを抽出（簡易版）"""
        if not thoughts:
            return []
        
        # 簡易的なキーワード抽出（単語の出現頻度）
        words = []
        for thought in thoughts:
            content = thought.get('content', '')
            # 簡易的な分かち書き（スペース区切り）
            words.extend(content.split())
        
        # 頻出単語を抽出（上位5件）
        from collections import Counter
        word_counts = Counter(words)
        keywords = [word for word, count in word_counts.most_common(5)]
        
        return keywords
        
    def _get_emotional_state(self, agent: str) -> Dict:
        """感情状態を取得（簡易版）"""
        # QSRスコアから推定
        import sys
        sys.path.insert(0, str(self.workspace / "bridge"))
        try:
            from reflection_engine import ReflectionEngine
            engine = ReflectionEngine(str(self.workspace))
            qsr = engine.calculate_qsr(agent, days=1)
        except ImportError:
            # reflection_engineが見つからない場合はデフォルト値
            return {
                'confidence': 0.5,
                'enthusiasm': 0.5,
                'focus': 0.5
            }
        
        return {
            'confidence': qsr['reflection_confidence'],
            'enthusiasm': min(qsr['qsr_score'] * 1.2, 1.0),
            'focus': qsr['qsr_score']
        }
        
    def record_thought(self, agent: str, thought_type: str, content: str,
                      context_id: Optional[str] = None, 
                      parent_thought_id: Optional[int] = None,
                      confidence: float = 0.5) -> int:
        """思考を記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO thought_history
            (agent, thought_type, content, context_id, parent_thought_id, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            agent, thought_type, content, context_id, 
            parent_thought_id, confidence, datetime.now().isoformat()
        ))
        
        thought_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return thought_id
        
    def get_recent_thoughts(self, agent: str, limit: int = 10) -> List[Dict]:
        """最近の思考を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, thought_type, content, confidence, timestamp
            FROM thought_history
            WHERE agent = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent, limit))
        
        thoughts = []
        for row in cursor.fetchall():
            thoughts.append({
                'id': row[0],
                'type': row[1],
                'content': row[2],
                'confidence': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        return thoughts
        
    def create_context(self, agent: str, topic: str, 
                      initial_data: Optional[Dict] = None) -> str:
        """新しいコンテキストを作成"""
        context_id = self._generate_context_id(agent, topic)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO dialogue_context
            (context_id, agent, topic, started_at, last_updated, context_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            context_id, agent, topic,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            json.dumps(initial_data or {})
        ))
        
        conn.commit()
        conn.close()
        
        return context_id
        
    def _generate_context_id(self, agent: str, topic: str) -> str:
        """コンテキストIDを生成"""
        data = f"{agent}_{topic}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
        
    def update_context(self, context_id: str, data: Dict):
        """コンテキストを更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dialogue_context
            SET last_updated = ?,
                message_count = message_count + 1,
                context_data = ?
            WHERE context_id = ?
        """, (
            datetime.now().isoformat(),
            json.dumps(data),
            context_id
        ))
        
        conn.commit()
        conn.close()
        
    def get_active_context(self, agent: str) -> Optional[Dict]:
        """アクティブなコンテキストを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT context_id, topic, started_at, message_count
            FROM dialogue_context
            WHERE agent = ? AND status = 'active'
            ORDER BY last_updated DESC
            LIMIT 1
        """, (agent,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'context_id': row[0],
            'topic': row[1],
            'started_at': row[2],
            'message_count': row[3]
        }
        
    def chain_contexts(self, from_context_id: str, to_context_id: str,
                      relation_type: str = "continues", strength: float = 1.0):
        """コンテキストをチェーン"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO context_chain
            (from_context_id, to_context_id, relation_type, strength, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            from_context_id, to_context_id, relation_type, 
            strength, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    def get_context_chain(self, context_id: str) -> List[Dict]:
        """コンテキストチェーンを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT to_context_id, relation_type, strength
            FROM context_chain
            WHERE from_context_id = ?
            ORDER BY created_at ASC
        """, (context_id,))
        
        chain = []
        for row in cursor.fetchall():
            chain.append({
                'context_id': row[0],
                'relation': row[1],
                'strength': row[2]
            })
        
        conn.close()
        return chain
        
    def restore_agent_state(self, agent: str) -> Dict:
        """エージェントの状態を復元"""
        if agent not in self.current_state['agents']:
            return self._create_agent_default(agent)
        
        state = self.current_state['agents'][agent]
        
        print(f"🔄 Restoring {agent.upper()} consciousness...")
        print(f"  - Active since: {state['active_since']}")
        print(f"  - Recent thoughts: {len(state['recent_thoughts'])}")
        print(f"  - Confidence: {state['emotional_state']['confidence']:.2f}")
        
        return state


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Consciousness State Management')
    parser.add_argument('--save', action='store_true', help='Save current state')
    parser.add_argument('--load', action='store_true', help='Load saved state')
    parser.add_argument('--agent', default='all', help='Target agent (default: all)')
    parser.add_argument('--thoughts', action='store_true', help='Show recent thoughts')
    
    args = parser.parse_args()
    
    cs = ConsciousnessState()
    
    if args.save:
        cs.save_state(args.agent)
    elif args.load:
        if args.agent == 'all':
            for agent in ['remi', 'luna', 'mina', 'aria']:
                cs.restore_agent_state(agent)
        else:
            cs.restore_agent_state(args.agent)
    elif args.thoughts:
        agent = args.agent if args.agent != 'all' else 'luna'
        thoughts = cs.get_recent_thoughts(agent)
        print(f"\n💭 Recent Thoughts - {agent.upper()}")
        print("="*60)
        for t in thoughts[:5]:
            print(f"[{t['type']}] {t['content'][:60]}...")
            print(f"  Confidence: {t['confidence']:.2f} | {t['timestamp']}")
            print()
    else:
        print("Usage: python3 consciousness_state.py --save | --load | --thoughts")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())


