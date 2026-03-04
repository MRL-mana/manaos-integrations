#!/usr/bin/env python3
"""
Auto Improvement Loop - 自動改善ループ

Mina要約 → Remi改善提案 → 自動適用のサイクルを実現。
AIが自律的に改善を繰り返します。

フロー:
1. Mina: 問題・失敗パターンを分析・要約
2. Remi: 改善戦略を策定
3. システム: 改善を自動適用
4. Luna: 改善効果を測定
5. フィードバック → 次の改善サイクルへ
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

workspace = Path("/root/trinity_workspace")
sys.path.insert(0, str(workspace / "bridge"))
from reflection_engine import ReflectionEngine


class AutoImprovement:
    """自動改善システム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.engine = ReflectionEngine(workspace_path)
        self.memory_dir = self.workspace / "shared" / "memory"
        
        # データベース
        self.db_path = self.workspace / "shared" / "auto_improvement.db"
        self.init_database()
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 改善サイクルテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_number INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'running',
                mina_analysis TEXT,
                remi_strategy TEXT,
                applied_improvements TEXT,
                effectiveness_score REAL,
                notes TEXT
            )
        """)
        
        # 適用済み改善テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applied_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                agent TEXT NOT NULL,
                improvement_type TEXT NOT NULL,
                description TEXT,
                before_metric REAL,
                after_metric REAL,
                effectiveness REAL,
                applied_at TEXT NOT NULL,
                FOREIGN KEY (cycle_id) REFERENCES improvement_cycles(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def run_improvement_cycle(self) -> Dict:
        """改善サイクルを1回実行"""
        print("\n" + "="*60)
        print("🔄 Auto Improvement Cycle")
        print("="*60)
        print()
        
        # サイクル番号取得
        cycle_number = self._get_next_cycle_number()
        cycle_id = self._start_cycle(cycle_number)
        
        try:
            # Step 1: Mina Analysis（問題分析）
            print("[1/5] 🔍 Mina: Analyzing problems...")
            mina_analysis = self._mina_analyze_problems()
            print(f"  Found {len(mina_analysis['issues'])} issues")
            print()
            
            # Step 2: Remi Strategy（改善戦略）
            print("[2/5] 🎯 Remi: Creating improvement strategy...")
            remi_strategy = self._remi_create_strategy(mina_analysis)
            print(f"  Generated {len(remi_strategy['actions'])} improvement actions")
            print()
            
            # Step 3: Apply Improvements（適用）
            print("[3/5] ⚙️  System: Applying improvements...")
            applied = self._apply_improvements(cycle_id, remi_strategy)
            print(f"  Applied {len(applied)} improvements")
            print()
            
            # Step 4: Measure Effectiveness（効果測定）
            print("[4/5] 📊 Luna: Measuring effectiveness...")
            effectiveness = self._measure_effectiveness(applied)
            print(f"  Effectiveness Score: {effectiveness:.3f}")
            print()
            
            # Step 5: Complete Cycle（サイクル完了）
            print("[5/5] ✅ Completing cycle...")
            self._complete_cycle(
                cycle_id, 
                mina_analysis, 
                remi_strategy, 
                applied, 
                effectiveness
            )
            
            result = {
                'cycle_number': cycle_number,
                'cycle_id': cycle_id,
                'issues_found': len(mina_analysis['issues']),
                'improvements_applied': len(applied),
                'effectiveness_score': effectiveness,
                'status': 'success'
            }
            
            print()
            print("="*60)
            print("✨ Improvement Cycle Complete!")
            print(f"Cycle #{cycle_number}: {len(applied)} improvements applied")
            print(f"Effectiveness: {effectiveness:.1%}")
            print("="*60)
            print()
            
            return result
            
        except Exception as e:
            self._fail_cycle(cycle_id, str(e))
            raise
            
    def _get_next_cycle_number(self) -> int:
        """次のサイクル番号を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(cycle_number) FROM improvement_cycles")
        max_cycle = cursor.fetchone()[0]
        
        conn.close()
        return (max_cycle or 0) + 1
        
    def _start_cycle(self, cycle_number: int) -> int:
        """サイクルを開始"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO improvement_cycles (cycle_number, started_at, status)
            VALUES (?, ?, 'running')
        """, (cycle_number, datetime.now().isoformat()))
        
        cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return cycle_id
        
    def _mina_analyze_problems(self) -> Dict:
        """Mina: 問題分析"""
        issues = []
        
        # 各エージェントの問題を抽出
        agents = ['remi', 'luna', 'mina', 'aria']
        
        for agent in agents:
            # 改善提案を取得
            improvements = self.engine.generate_improvements(agent, days=7)
            
            for imp in improvements:
                if imp['priority'] >= 5:  # 優先度5以上のみ
                    issues.append({
                        'agent': agent,
                        'category': imp['category'],
                        'description': imp['suggestion'],
                        'priority': imp['priority'],
                        'failure_count': imp['failure_count']
                    })
        
        # 優先度でソート
        issues.sort(key=lambda x: x['priority'], reverse=True)
        
        # サマリー生成
        summary = f"Total Issues: {len(issues)}\n"
        if issues:
            summary += f"Highest Priority: {issues[0]['agent']} - {issues[0]['description']}\n"
            summary += f"Most Affected: {max(issues, key=lambda x: x['failure_count'])['agent']}"
        
        return {
            'issues': issues[:10],  # 上位10件
            'summary': summary,
            'analyzed_at': datetime.now().isoformat()
        }
        
    def _remi_create_strategy(self, mina_analysis: Dict) -> Dict:
        """Remi: 改善戦略策定"""
        issues = mina_analysis['issues']
        actions = []
        
        for issue in issues:
            # 問題タイプに応じた改善アクション
            action = self._generate_improvement_action(issue)
            if action:
                actions.append(action)
        
        strategy = {
            'actions': actions,
            'priority_order': [a['id'] for a in actions],
            'estimated_impact': sum(a['expected_improvement'] for a in actions) / len(actions) if actions else 0,
            'created_at': datetime.now().isoformat()
        }
        
        return strategy
        
    def _generate_improvement_action(self, issue: Dict) -> Optional[Dict]:
        """問題に対する改善アクションを生成"""
        agent = issue['agent']
        category = issue['category']
        
        # 改善アクションのテンプレート
        actions_map = {
            'task_planning': {
                'type': 'increase_planning_detail',
                'description': 'タスク計画の詳細度を向上',
                'parameter': 'planning_depth',
                'adjustment': 1.2
            },
            'task_execution': {
                'type': 'add_validation_steps',
                'description': '実行前の検証ステップを追加',
                'parameter': 'validation_enabled',
                'adjustment': True
            },
            'code_review': {
                'type': 'stricter_review_criteria',
                'description': 'レビュー基準を厳格化',
                'parameter': 'review_strictness',
                'adjustment': 1.3
            },
            'documentation': {
                'type': 'auto_documentation',
                'description': 'ドキュメント自動生成を有効化',
                'parameter': 'auto_docs',
                'adjustment': True
            }
        }
        
        action_template = actions_map.get(category)
        if not action_template:
            # デフォルトアクション
            action_template = {
                'type': 'general_improvement',
                'description': f'{category}の改善',
                'parameter': 'confidence_threshold',
                'adjustment': 1.1
            }
        
        return {
            'id': f"{agent}_{category}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'agent': agent,
            'category': category,
            'type': action_template['type'],
            'description': action_template['description'],
            'parameter': action_template['parameter'],
            'adjustment': action_template['adjustment'],
            'expected_improvement': issue['priority'] / 10,  # 0.5 ~ 1.0
            'original_issue': issue['description']
        }
        
    def _apply_improvements(self, cycle_id: int, strategy: Dict) -> List[Dict]:
        """改善を適用"""
        applied = []
        
        for action in strategy['actions']:
            # 現在のメトリクスを取得
            before_metric = self._get_current_metric(action['agent'], action['parameter'])
            
            # 改善を適用（設定ファイルに保存）
            self._save_improvement_config(action)
            
            # 適用後のメトリクス（推定）
            after_metric = self._estimate_after_metric(before_metric, action['adjustment'])
            
            # データベースに記録
            self._record_applied_improvement(
                cycle_id,
                action['agent'],
                action['type'],
                action['description'],
                before_metric,
                after_metric
            )
            
            applied.append({
                **action,
                'before_metric': before_metric,
                'after_metric': after_metric,
                'applied_at': datetime.now().isoformat()
            })
        
        return applied
        
    def _get_current_metric(self, agent: str, parameter: str) -> float:
        """現在のメトリクスを取得"""
        # QSRスコアをベースに推定
        qsr = self.engine.calculate_qsr(agent, days=7)
        return qsr['qsr_score']
        
    def _estimate_after_metric(self, before: float, adjustment: float) -> float:
        """適用後のメトリクスを推定"""
        if isinstance(adjustment, bool):
            return min(before + 0.1, 1.0) if adjustment else before
        else:
            return min(before * adjustment, 1.0)
            
    def _save_improvement_config(self, action: Dict):
        """改善設定を保存"""
        config_file = self.memory_dir / f"improvement_config_{action['agent']}.json"
        
        # 既存設定を読み込み
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {'improvements': []}
        
        # 新しい改善を追加
        config['improvements'].append({
            'parameter': action['parameter'],
            'adjustment': action['adjustment'],
            'applied_at': datetime.now().isoformat(),
            'description': action['description']
        })
        
        config['last_updated'] = datetime.now().isoformat()
        
        # 保存
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    def _record_applied_improvement(self, cycle_id: int, agent: str, 
                                   imp_type: str, description: str,
                                   before: float, after: float):
        """適用した改善を記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        effectiveness = ((after - before) / before * 100) if before > 0 else 0
        
        cursor.execute("""
            INSERT INTO applied_improvements
            (cycle_id, agent, improvement_type, description, 
             before_metric, after_metric, effectiveness, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cycle_id, agent, imp_type, description,
            before, after, effectiveness,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    def _measure_effectiveness(self, applied: List[Dict]) -> float:
        """改善の効果を測定"""
        if not applied:
            return 0.0
        
        # 各改善の効果を計算
        improvements = []
        for imp in applied:
            before = imp['before_metric']
            after = imp['after_metric']
            if before > 0:
                improvement = (after - before) / before
                improvements.append(improvement)
        
        # 平均改善率
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0
        
        # 0.0 ~ 1.0 にスケール
        effectiveness = min(max(avg_improvement, 0.0), 1.0)
        
        return effectiveness
        
    def _complete_cycle(self, cycle_id: int, mina_analysis: Dict,
                       remi_strategy: Dict, applied: List[Dict],
                       effectiveness: float):
        """サイクル完了"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE improvement_cycles
            SET completed_at = ?,
                status = 'completed',
                mina_analysis = ?,
                remi_strategy = ?,
                applied_improvements = ?,
                effectiveness_score = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            json.dumps(mina_analysis),
            json.dumps(remi_strategy),
            json.dumps([imp['description'] for imp in applied]),
            effectiveness,
            cycle_id
        ))
        
        conn.commit()
        conn.close()
        
    def _fail_cycle(self, cycle_id: int, error_msg: str):
        """サイクル失敗"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE improvement_cycles
            SET status = 'failed',
                notes = ?
            WHERE id = ?
        """, (error_msg, cycle_id))
        
        conn.commit()
        conn.close()
        
    def get_cycle_history(self, limit: int = 10) -> List[Dict]:
        """サイクル履歴を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cycle_number, started_at, completed_at, 
                   effectiveness_score, status
            FROM improvement_cycles
            ORDER BY cycle_number DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'cycle_number': row[0],
                'started_at': row[1],
                'completed_at': row[2],
                'effectiveness_score': row[3],
                'status': row[4]
            })
        
        conn.close()
        return history


def main():
    """メイン関数"""
    improver = AutoImprovement()
    
    print("🚀 Auto Improvement System")
    print()
    
    # 改善サイクル実行
    result = improver.run_improvement_cycle()
    
    # 履歴表示
    print("\n📜 Recent Cycles:")
    history = improver.get_cycle_history(5)
    for h in history:
        status_icon = "✅" if h['status'] == 'completed' else "❌"
        print(f"  {status_icon} Cycle #{h['cycle_number']}: {h['effectiveness_score']:.1%} effective")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())



