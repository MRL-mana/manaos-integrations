#!/usr/bin/env python3
"""
DiscoRL ManaOS Learning Integration
DiscoRLをManaOSの学習システムに統合
"""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# ManaOS統合
sys.path.append('/root/manaos_agents')

try:
    from ai_learning_integration import AgentLearningBridge
    MANAOS_AVAILABLE = True
except ImportError:
    print("⚠️  ManaOS Agentsが見つかりません")
    MANAOS_AVAILABLE = False


class DiscoRLManaOSBridge:
    """DiscoRLとManaOS学習システムのブリッジ"""
    
    def __init__(self):
        self.learning_bridge = AgentLearningBridge() if MANAOS_AVAILABLE else None  # type: ignore[possibly-unbound]
        self.db_path = Path("/root/manaos_unified_system/data/learning.db")
        
    def save_discorl_results(
        self,
        phase: str,
        results: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        DiscoRLの実験結果をManaOSに保存
        
        Args:
            phase: Phase名（Phase1, Phase2, Phase3）
            results: 実験結果
            config: 設定情報
            
        Returns:
            保存成功したかどうか
        """
        if not MANAOS_AVAILABLE:
            print("⚠️  ManaOS統合が無効です")
            return False
        
        try:
            # ManaOSの学習データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # DiscoRL実験テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discorl_experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    phase TEXT,
                    config TEXT,
                    results TEXT,
                    summary TEXT,
                    success_rate REAL,
                    notes TEXT
                )
            ''')
            
            # 結果を保存
            timestamp = datetime.now().isoformat()
            summary = self._create_summary(phase, results)
            success_rate = results.get('final_success_rate', results.get('final_avg_reward', 0))
            
            cursor.execute('''
                INSERT INTO discorl_experiments 
                (timestamp, phase, config, results, summary, success_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                phase,
                json.dumps(config) if config else None,
                json.dumps(results),
                summary,
                float(success_rate) if success_rate else 0.0,
                f"DiscoRL {phase} experiment results"
            ))
            
            conn.commit()
            conn.close()
            
            # AgentLearningBridgeにも保存
            task = f"DiscoRL {phase} Experiment"
            result_text = f"""Phase: {phase}
Results: {json.dumps(results, indent=2)}
Summary: {summary}
Success Rate: {success_rate}
"""
            
            self.learning_bridge.save_agent_knowledge(  # type: ignore[union-attr]
                agent_name="DiscoRL",
                task=task,
                result=result_text,
                category="reinforcement_learning",
                importance=8,
                tags=["discorl", "rl", "meta-learning", phase.lower()]
            )
            
            print("✅ DiscoRL実験結果をManaOS学習システムに保存しました")
            return True
            
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
            return False
    
    def search_discorl_knowledge(
        self,
        query: str,
        phase: Optional[str] = None
    ) -> list:
        """DiscoRLの過去の実験結果を検索"""
        if not MANAOS_AVAILABLE:
            return []
        
        try:
            # ManaOSの学習データベースから検索
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if phase:
                cursor.execute('''
                    SELECT * FROM discorl_experiments 
                    WHERE phase = ? 
                    ORDER BY timestamp DESC LIMIT 10
                ''', (phase,))
            else:
                cursor.execute('''
                    SELECT * FROM discorl_experiments 
                    ORDER BY timestamp DESC LIMIT 10
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            # AgentLearningBridgeからも検索
            bridge_results = self.learning_bridge.search_agent_knowledge(  # type: ignore[union-attr]
                query=query,
                agent_name="DiscoRL",
                limit=5
            )
            
            return results + bridge_results
            
        except Exception as e:
            print(f"❌ 検索エラー: {e}")
            return []
    
    def _create_summary(self, phase: str, results: Dict[str, Any]) -> str:
        """結果のサマリーを作成"""
        if phase == "Phase2":
            return "Comparison experiment: Actor-Critic vs Disco103"
        elif phase == "Phase3":
            success_rate = results.get('final_success_rate', 0)
            return f"Web automation applicability: {success_rate:.1%}"
        else:
            return "Phase experiment completed"
    
    def get_recommendations(self) -> Dict[str, Any]:
        """ManaOS学習システムから推奨事項を取得"""
        if not MANAOS_AVAILABLE:
            return {}
        
        try:
            # 過去の実験結果から学習
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 最良の設定を取得
            cursor.execute('''
                SELECT * FROM discorl_experiments 
                WHERE success_rate > 0.3
                ORDER BY success_rate DESC LIMIT 1
            ''')
            
            best_result = cursor.fetchone()
            conn.close()
            
            if best_result:
                return {
                    'recommended_config': json.loads(best_result[3]) if best_result[3] else {},
                    'best_success_rate': best_result[6],
                    'notes': best_result[7]
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ 推奨事項取得エラー: {e}")
            return {}


def main():
    """統合テスト"""
    print("=" * 60)
    print("DiscoRL ManaOS Integration Test")
    print("=" * 60)
    
    bridge = DiscoRLManaOSBridge()
    
    # テストデータ
    test_results = {
        'phase': 'Phase2',
        'final_avg_reward': -0.1000,
        'final_success_rate': 0.0,
        'config': {
            'num_steps': 500,
            'seed': 42
        }
    }
    
    # ManaOSに保存
    success = bridge.save_discorl_results(
        phase='Phase2',
        results=test_results,
        config={'num_steps': 500}
    )
    
    if success:
        print("\n✅ ManaOS統合成功！")
        print("DiscoRLの実験結果がManaOS学習システムに保存されました")
    else:
        print("\n⚠️  ManaOS統合が無効です")
    
    # 推奨事項取得
    recommendations = bridge.get_recommendations()
    if recommendations:
        print("\n📊 推奨事項:")
        print(json.dumps(recommendations, indent=2))


if __name__ == '__main__':
    main()
