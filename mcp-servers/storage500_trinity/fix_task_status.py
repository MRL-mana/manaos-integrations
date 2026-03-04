#!/usr/bin/env python3
"""
タスクステータス一括修正スクリプト

Phase 1-2の完了済みタスクを正確にマーク
"""

import sys
sys.path.insert(0, '/root/trinity_workspace/core')

from db_manager import DatabaseManager
from datetime import datetime

def main():
    db = DatabaseManager()
    
    print("🔧 タスクステータス修正開始...\n")
    
    # Phase 1 完了タスク
    phase1_tasks = [
        'PHASE1-001',  # file_watcher.py
        'PHASE1-002',  # autonomous_orchestrator.py
        'PHASE1-003',  # db_manager.py
        'PHASE1-004',  # trinity_cli.py
    ]
    
    # Phase 2 完了タスク
    phase2_tasks = [
        'PHASE2-001',  # agent_manager.py
        'PHASE2-002',  # agent_remi.py
        'PHASE2-003',  # agent_luna.py
        'PHASE2-004',  # agent_mina.py
        'PHASE2-005',  # agent_aria.py
    ]
    
    completed_tasks = phase1_tasks + phase2_tasks
    timestamp = datetime.now().isoformat()
    
    for task_id in completed_tasks:
        try:
            # タスク取得
            task = db.get_task(task_id)
            if not task:
                print(f"⚠️  タスク {task_id} が見つかりません")
                continue
            
            # ステータス更新
            if task['status'] != 'done':
                db.update_task(task_id, {
                    'status': 'done',
                    'completed_at': timestamp
                })
                print(f"✅ {task_id}: {task['status']} → done")
            else:
                print(f"✓  {task_id}: 既に完了済み")
        
        except Exception as e:
            print(f"❌ {task_id}: エラー - {e}")
    
    print(f"\n🎉 修正完了！")
    
    # 統計表示
    stats = db.get_task_stats()
    print(f"\n📊 現在の統計:")
    print(f"  総タスク数: {stats['total']}")
    print(f"  完了: {stats['done']} ({stats['done']/stats['total']*100:.1f}%)")
    print(f"  進行中: {stats['in_progress']}")
    print(f"  TODO: {stats['todo']}")
    print(f"  レビュー待ち: {stats['review']}")

if __name__ == '__main__':
    main()

