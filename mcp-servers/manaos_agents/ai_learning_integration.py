#!/usr/bin/env python3
"""
AI Learning System Integration for ManaOS Agents
エージェントの学習結果をAI Learning Systemに保存し、活用する
"""

import sys
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# AI Learning Systemのパスを追加
sys.path.insert(0, '/root/ai_learning_system')

try:
    from core.knowledge_manager import KnowledgeManager
    AI_LEARNING_AVAILABLE = True
except ImportError:
    print("⚠️  AI Learning Systemが見つかりません")
    AI_LEARNING_AVAILABLE = False


class AgentLearningBridge:
    """エージェントとAI Learning Systemを繋ぐブリッジ"""
    
    def __init__(self):
        self.learning_system = KnowledgeManager() if AI_LEARNING_AVAILABLE else None
        self.db_path = self.learning_system.db_path if self.learning_system else None
        
    def save_agent_knowledge(
        self,
        agent_name: str,
        task: str,
        result: str,
        category: str = "agent_task",
        importance: int = 5,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        エージェントの実行結果を学習システムに保存
        
        Args:
            agent_name: エージェント名
            task: 実行したタスク
            result: 結果
            category: カテゴリ
            importance: 重要度 (1-10)
            tags: タグリスト
            
        Returns:
            保存成功したかどうか
        """
        if not self.learning_system:
            return False
            
        try:
            # タグにエージェント名を追加
            if tags is None:
                tags = []
            tags.append(f"agent:{agent_name}")
            tags.append("manaos_agents")
            
            # 知識として保存
            content = f"""
【エージェント】{agent_name}
【タスク】{task}
【結果】
{result}
【実行日時】{datetime.now().isoformat()}
"""
            
            title = f"{agent_name}: {task[:50]}"
            
            knowledge_id = self.learning_system.store(
                content=content,
                title=title,
                category=category,
                importance=importance,
                tags=tags
            )
            
            if knowledge_id:
                print(f"✅ 学習システムに保存しました (ID: {knowledge_id})")
                return True
            return False
            
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
            return False
    
    def search_agent_knowledge(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        エージェントの過去の知識を検索
        
        Args:
            query: 検索クエリ
            agent_name: 特定のエージェントに絞り込み
            limit: 最大結果数
            
        Returns:
            検索結果のリスト
        """
        if not self.learning_system:
            return []
            
        try:
            # タグフィルタを設定
            tags = ["manaos_agents"]
            if agent_name:
                tags.append(f"agent:{agent_name}")
            
            results = self.learning_system.retrieve(
                query=query,
                tags=tags,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            print(f"❌ 検索エラー: {e}")
            return []
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """エージェントの統計情報を取得"""
        if not self.learning_system:
            return {}
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # エージェント別のタスク数を取得
            cursor.execute("""
                SELECT 
                    json_extract(content, '$[0]') as agent_name,
                    COUNT(*) as task_count
                FROM knowledge
                WHERE content LIKE '%エージェント%'
                GROUP BY agent_name
            """)
            
            stats = {
                "total_tasks": 0,
                "agents": {}
            }
            
            for row in cursor.fetchall():
                agent_name = row[0]
                task_count = row[1]
                stats["agents"][agent_name] = task_count
                stats["total_tasks"] += task_count
            
            conn.close()
            return stats
            
        except Exception as e:
            print(f"❌ 統計取得エラー: {e}")
            return {}
    
    def get_recent_agent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のエージェント活動を取得"""
        if not self.learning_system:
            return []
            
        try:
            results = self.learning_system.retrieve(
                query="エージェント",
                tags=["manaos_agents"],
                limit=limit
            )
            
            activities = []
            for result in results:
                activities.append({
                    "id": result.get("id"),
                    "title": result.get("title"),
                    "created_at": result.get("created_at"),
                    "importance": result.get("importance")
                })
            
            return activities
            
        except Exception as e:
            print(f"❌ 活動履歴取得エラー: {e}")
            return []
    
    def create_agent_from_knowledge(
        self,
        knowledge_id: int,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        過去の知識からエージェントの行動パターンを学習
        
        Args:
            knowledge_id: 学習する知識のID
            agent_name: エージェント名
            
        Returns:
            学習したパターン情報
        """
        if not self.learning_system:
            return None
            
        try:
            # 知識を取得
            knowledge = self.learning_system.get(knowledge_id)
            if not knowledge:
                return None
            
            # パターンを抽出（簡易実装）
            content = knowledge.get("content", "")
            
            pattern = {
                "agent_name": agent_name,
                "learned_from": knowledge_id,
                "timestamp": datetime.now().isoformat(),
                "content_summary": content[:200],
                "tags": knowledge.get("tags", [])
            }
            
            return pattern
            
        except Exception as e:
            print(f"❌ パターン学習エラー: {e}")
            return None


# === 便利な関数 ===

def quick_save_agent_result(agent_name: str, task: str, result: str) -> bool:
    """エージェントの結果を素早く保存"""
    bridge = AgentLearningBridge()
    return bridge.save_agent_knowledge(agent_name, task, result)


def quick_search_agent_history(query: str, agent: Optional[str] = None) -> List[Dict]:
    """エージェントの履歴を素早く検索"""
    bridge = AgentLearningBridge()
    return bridge.search_agent_knowledge(query, agent)


def show_agent_stats():
    """エージェントの統計を表示"""
    bridge = AgentLearningBridge()
    stats = bridge.get_agent_stats()
    
    print("\n📊 エージェント統計")
    print("="*50)
    print(f"総タスク数: {stats.get('total_tasks', 0)}")
    print("\nエージェント別:")
    for agent, count in stats.get("agents", {}).items():
        print(f"  {agent}: {count}タスク")


def show_recent_activities(limit: int = 10):
    """最近の活動を表示"""
    bridge = AgentLearningBridge()
    activities = bridge.get_recent_agent_activities(limit)
    
    print(f"\n📋 最近のエージェント活動 (最新{limit}件)")
    print("="*50)
    for activity in activities:
        print(f"[{activity['created_at']}] {activity['title']}")
        print(f"  重要度: {activity['importance']}/10")
        print()


if __name__ == "__main__":
    print("🔗 Agent Learning Bridge - テスト")
    print("="*50)
    
    if not AI_LEARNING_AVAILABLE:
        print("❌ AI Learning Systemが利用できません")
        sys.exit(1)
    
    bridge = AgentLearningBridge()
    
    # テスト保存
    test_saved = bridge.save_agent_knowledge(
        agent_name="TestAgent",
        task="システムテスト",
        result="正常に動作しています",
        importance=7,
        tags=["test", "system_check"]
    )
    
    if test_saved:
        print("\n✅ テスト保存成功!")
    
    # 統計表示
    show_agent_stats()
    
    # 最近の活動表示
    show_recent_activities(5)
    
    print("\n✅ Bridge初期化完了!")

