#!/usr/bin/env python3
"""
Reflection Engine - 自己反省・学習ループエンジン

AIエージェントが自身の行動と結果を振り返り、
継続的に改善するための自己反省システム。

主要機能:
- 行動と結果の記録
- パターン認識と学習
- 改善提案の生成
- QSR（Quality Self Reflection）スコア計算
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math


class ReflectionEngine:
    """自己反省エンジン"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.shared_dir = self.workspace / "shared"
        self.memory_dir = self.shared_dir / "memory"
        
        # データベース
        self.db_path = self.shared_dir / "reflection_memory.db"
        self.init_database()
        
        # 学習パラメータ
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        
    def init_database(self):
        """反省記憶データベースの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 行動記録テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                action_type TEXT NOT NULL,
                context TEXT,
                decision_reasoning TEXT,
                confidence REAL DEFAULT 0.5
            )
        """)
        
        # 結果記録テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                actual_result TEXT,
                expected_result TEXT,
                deviation_score REAL,
                FOREIGN KEY (action_id) REFERENCES actions(id)
            )
        """)
        
        # 学習パターンテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                agent TEXT NOT NULL,
                description TEXT,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                confidence REAL DEFAULT 0.5
            )
        """)
        
        # 改善提案テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                category TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                applied BOOLEAN DEFAULT 0
            )
        """)
        
        # QSRスコアテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qsr_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                qsr_score REAL NOT NULL,
                reflection_confidence REAL,
                learning_delta REAL,
                notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
    def record_action(self, agent: str, action_type: str, 
                     context: str, reasoning: str, confidence: float = 0.5) -> int:
        """行動を記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO actions 
            (timestamp, agent, action_type, context, decision_reasoning, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            agent,
            action_type,
            context,
            reasoning,
            confidence
        ))
        
        action_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return action_id
        
    def record_outcome(self, action_id: int, success: bool,
                      actual_result: str, expected_result: str) -> float:
        """結果を記録し、偏差スコアを計算"""
        # 偏差スコアを計算
        deviation_score = self._calculate_deviation(
            actual_result, expected_result, success
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO outcomes 
            (action_id, timestamp, success, actual_result, expected_result, deviation_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            action_id,
            datetime.now().isoformat(),
            success,
            actual_result,
            expected_result,
            deviation_score
        ))
        
        conn.commit()
        conn.close()
        
        # パターン学習をトリガー
        self._learn_from_outcome(action_id, success, deviation_score)
        
        return deviation_score
        
    def _calculate_deviation(self, actual: str, expected: str, success: bool) -> float:
        """偏差スコアを計算"""
        if success:
            # 成功時は結果の一致度を評価
            similarity = self._text_similarity(actual, expected)
            return 1.0 - similarity  # 偏差は低いほど良い
        else:
            # 失敗時は高い偏差
            return 0.8
            
    def _text_similarity(self, text1: str, text2: str) -> float:
        """テキストの類似度を簡易計算"""
        # 簡易実装：単語の重複率
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    def _learn_from_outcome(self, action_id: int, success: bool, deviation: float):
        """結果から学習"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # アクション情報を取得
        cursor.execute("""
            SELECT agent, action_type, context 
            FROM actions WHERE id = ?
        """, (action_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
            
        agent, action_type, context = row
        
        # 既存パターンを検索
        cursor.execute("""
            SELECT id, success_rate, usage_count, confidence
            FROM learned_patterns
            WHERE agent = ? AND pattern_type = ?
        """, (agent, action_type))
        
        pattern = cursor.fetchone()
        
        if pattern:
            # 既存パターンを更新
            pattern_id, old_success_rate, usage_count, old_confidence = pattern
            
            # 成功率を更新（移動平均）
            new_usage_count = usage_count + 1
            success_value = 1.0 if success else 0.0
            new_success_rate = (
                (old_success_rate * usage_count + success_value) / new_usage_count
            )
            
            # 信頼度を更新（経験が増えるほど上昇）
            new_confidence = min(0.99, old_confidence + self.learning_rate * (1.0 - deviation))
            
            cursor.execute("""
                UPDATE learned_patterns
                SET success_rate = ?, usage_count = ?, last_used = ?, confidence = ?
                WHERE id = ?
            """, (
                new_success_rate,
                new_usage_count,
                datetime.now().isoformat(),
                new_confidence,
                pattern_id
            ))
        else:
            # 新しいパターンを作成
            success_rate = 1.0 if success else 0.0
            confidence = 0.5 + self.learning_rate * (1.0 - deviation)
            
            cursor.execute("""
                INSERT INTO learned_patterns
                (pattern_type, agent, description, success_rate, usage_count, last_used, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action_type,
                agent,
                f"Pattern learned from context: {context[:100]}",
                success_rate,
                1,
                datetime.now().isoformat(),
                confidence
            ))
            
        conn.commit()
        conn.close()
        
    def generate_improvements(self, agent: Optional[str] = None, 
                             days: int = 7) -> List[Dict]:
        """改善提案を生成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 過去N日間の失敗を分析
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = """
            SELECT a.agent, a.action_type, COUNT(*) as failure_count
            FROM actions a
            JOIN outcomes o ON a.id = o.action_id
            WHERE o.success = 0 AND a.timestamp > ?
        """
        params = [since]
        
        if agent:
            query += " AND a.agent = ?"
            params.append(agent)
            
        query += " GROUP BY a.agent, a.action_type ORDER BY failure_count DESC"
        
        cursor.execute(query, params)
        
        improvements = []
        for row in cursor.fetchall():
            agent_name, action_type, failure_count = row
            
            # 改善提案を生成
            suggestion = self._generate_suggestion(agent_name, action_type, failure_count)
            priority = min(10, failure_count)
            
            # データベースに記録
            cursor.execute("""
                INSERT INTO improvements
                (timestamp, agent, category, suggestion, priority, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                agent_name,
                action_type,
                suggestion,
                priority,
                'pending'
            ))
            
            improvements.append({
                'agent': agent_name,
                'category': action_type,
                'suggestion': suggestion,
                'priority': priority,
                'failure_count': failure_count
            })
            
        conn.commit()
        conn.close()
        
        return improvements
        
    def _generate_suggestion(self, agent: str, action_type: str, 
                           failure_count: int) -> str:
        """改善提案を生成"""
        templates = {
            'high': f"{agent}の{action_type}で{failure_count}回の失敗が検出されました。実装ロジックの見直しを推奨します。",
            'medium': f"{agent}の{action_type}の成功率が低下しています。パラメータ調整を検討してください。",
            'low': f"{agent}の{action_type}で軽微な問題が発生しています。経過観察を推奨します。"
        }
        
        if failure_count >= 5:
            return templates['high']
        elif failure_count >= 3:
            return templates['medium']
        else:
            return templates['low']
            
    def calculate_qsr(self, agent: Optional[str] = None, 
                     days: int = 7) -> Dict:
        """QSR（Quality Self Reflection）スコアを計算"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 成功率を計算
        query = """
            SELECT 
                COUNT(CASE WHEN o.success = 1 THEN 1 END) as successes,
                COUNT(*) as total
            FROM actions a
            JOIN outcomes o ON a.id = o.action_id
            WHERE a.timestamp > ?
        """
        params = [since]
        
        if agent:
            query += " AND a.agent = ?"
            params.append(agent)
            
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if not row or row[1] == 0:
            conn.close()
            return {
                'qsr_score': 0.5,
                'reflection_confidence': 0.0,
                'learning_delta': 0.0,
                'message': 'Insufficient data'
            }
            
        successes, total = row
        success_rate = successes / total
        
        # 平均信頼度を計算
        query = """
            SELECT AVG(confidence)
            FROM learned_patterns
            WHERE last_used > ?
        """
        params = [since]
        
        if agent:
            query += " AND agent = ?"
            params.append(agent)
            
        cursor.execute(query, params)
        avg_confidence = cursor.fetchone()[0] or 0.5
        
        # 学習変化率を計算
        if agent:
            query = """
                SELECT 
                    (SELECT COUNT(*) FROM learned_patterns WHERE last_used > ? AND agent = ?) as new_patterns,
                    (SELECT COUNT(*) FROM learned_patterns WHERE agent = ?) as total_patterns
            """
            params = [since, agent, agent]
        else:
            query = """
                SELECT 
                    (SELECT COUNT(*) FROM learned_patterns WHERE last_used > ?) as new_patterns,
                    (SELECT COUNT(*) FROM learned_patterns) as total_patterns
            """
            params = [since]
            
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        new_patterns, total_patterns = row
        learning_delta = (new_patterns / total_patterns * 100) if total_patterns > 0 else 0
        
        # QSRスコアを計算
        qsr_score = (
            success_rate * 0.6 +  # 成功率: 60%
            avg_confidence * 0.3 +  # 信頼度: 30%
            min(learning_delta / 10, 0.1)  # 学習率: 10%
        )
        
        # データベースに記録
        cursor.execute("""
            INSERT INTO qsr_scores
            (timestamp, agent, qsr_score, reflection_confidence, learning_delta)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            agent or 'all',
            qsr_score,
            avg_confidence,
            learning_delta
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'qsr_score': round(qsr_score, 3),
            'reflection_confidence': round(avg_confidence, 3),
            'learning_delta': round(learning_delta, 2),
            'success_rate': round(success_rate, 3),
            'total_actions': total
        }
        
    def reflect_on_period(self, agent: str, days: int = 1) -> Dict:
        """期間の振り返りを実行"""
        print(f"\n=== Reflection: {agent} (past {days} days) ===")
        
        # QSRスコア計算
        qsr = self.calculate_qsr(agent, days)
        
        # 改善提案生成
        improvements = self.generate_improvements(agent, days)
        
        # レポート生成
        report = {
            'agent': agent,
            'period_days': days,
            'timestamp': datetime.now().isoformat(),
            'qsr_metrics': qsr,
            'improvements': improvements,
            'summary': self._generate_summary(qsr, improvements)
        }
        
        # ファイルに保存
        report_file = self.memory_dir / f"reflection_{agent}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        return report
        
    def _generate_summary(self, qsr: Dict, improvements: List[Dict]) -> str:
        """サマリーを生成"""
        qsr_score = qsr['qsr_score']
        
        if qsr_score >= 0.9:
            quality = "優秀"
        elif qsr_score >= 0.7:
            quality = "良好"
        elif qsr_score >= 0.5:
            quality = "普通"
        else:
            quality = "要改善"
            
        summary = f"総合評価: {quality} (QSR: {qsr_score})\n"
        summary += f"学習進捗: +{qsr['learning_delta']}%\n"
        
        if improvements:
            summary += f"\n改善提案: {len(improvements)}件"
        else:
            summary += "\n改善提案: なし（順調）"
            
        return summary
        
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 総行動数
        cursor.execute("SELECT COUNT(*) FROM actions")
        total_actions = cursor.fetchone()[0]
        
        # 総パターン数
        cursor.execute("SELECT COUNT(*) FROM learned_patterns")
        total_patterns = cursor.fetchone()[0]
        
        # 改善提案数
        cursor.execute("SELECT COUNT(*) FROM improvements WHERE status = 'pending'")
        pending_improvements = cursor.fetchone()[0]
        
        # エージェント別統計
        cursor.execute("""
            SELECT agent, COUNT(*) as action_count
            FROM actions
            GROUP BY agent
        """)
        agent_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_actions': total_actions,
            'total_patterns': total_patterns,
            'pending_improvements': pending_improvements,
            'agent_statistics': agent_stats
        }


def main():
    """メイン関数"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Reflection Engine')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--test', action='store_true', help='Run test mode')
    
    args = parser.parse_args()
    
    engine = ReflectionEngine()
    
    if args.test:
        # テストモード
        print("=== Reflection Engine Test ===")
        print(f"Database: {engine.db_path}")
        
        action_id = engine.record_action(
            agent='remi',
            action_type='task_planning',
            context='Creating new feature specification',
            reasoning='Based on user requirements',
            confidence=0.8
        )
        print(f"\nRecorded action ID: {action_id}")
        
        deviation = engine.record_outcome(
            action_id=action_id,
            success=True,
            actual_result='Feature spec created successfully',
            expected_result='Create detailed feature specification'
        )
        print(f"Outcome recorded, deviation: {deviation:.3f}")
        
        qsr = engine.calculate_qsr(agent='remi', days=30)
        print(f"\nQSR Metrics:")
        print(json.dumps(qsr, indent=2))
        
        stats = engine.get_statistics()
        print(f"\nStatistics:")
        print(json.dumps(stats, indent=2))
    else:
        # Daemonモード（定期的な振り返り実行）
        print("🚀 Reflection Engine starting...")
        print(f"Database: {engine.db_path}")
        
        try:
            print("✅ Reflection Engine running (Ctrl+C to stop)")
            print("   Performing reflections every 6 hours...")
            
            while True:
                # 6時間ごとに振り返り実行
                for agent in ['remi', 'luna', 'mina', 'aria']:
                    try:
                        report = engine.reflect_on_period(agent, days=1)
                        print(f"[INFO] Reflection completed for {agent}")
                    except Exception as e:
                        print(f"[ERROR] Reflection failed for {agent}: {e}")
                
                time.sleep(6 * 3600)  # 6時間待機
                
        except KeyboardInterrupt:
            print("\n⏹️  Shutting down...")
        finally:
            print("👋 Reflection Engine stopped")


if __name__ == '__main__':
    main()

