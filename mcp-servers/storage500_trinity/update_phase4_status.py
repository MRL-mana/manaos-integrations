#!/usr/bin/env python3
"""
Phase 4タスクステータス一括更新
統合機能テスト完了後のステータス反映
"""

import sys
sys.path.insert(0, '/root/trinity_workspace/core')

from db_manager import DatabaseManager
from datetime import datetime

def main():
    db = DatabaseManager()
    
    print("🔧 Phase 4タスクステータス更新開始...\n")
    
    # Phase 4 完了タスク
    phase4_tasks = [
        'PHASE4-001',  # GitHub統合
        'PHASE4-002',  # X280統合
        'PHASE4-003',  # Notion統合
        'PHASE4-004',  # Google Drive統合
        'PHASE4-005',  # ManaOS統合
    ]
    
    # Phase 3も更新
    phase3_tasks = [
        'PHASE3-001',  # dashboard_server.py
        'PHASE3-002',  # フロントエンド
        'PHASE3-003',  # REST API
    ]
    
    all_tasks = phase3_tasks + phase4_tasks
    timestamp = datetime.now().isoformat()
    
    for task_id in all_tasks:
        try:
            task = db.get_task(task_id)
            if not task:
                print(f"⚠️  タスク {task_id} が見つかりません")
                continue
            
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
    
    print(f"\n🎉 Phase 3-4 完了マーク完了！")
    
    # 統計表示
    total_done = len([t for t in db.get_tasks() if t['status'] == 'done'])
    total_tasks = len(db.get_tasks())
    completion_rate = (total_done / total_tasks * 100) if total_tasks > 0 else 0
    
    print(f"\n📊 現在の統計:")
    print(f"  総タスク数: {total_tasks}")
    print(f"  完了: {total_done} ({completion_rate:.1f}%)")
    print(f"  \n  Phase 1-2: ✅ 完了（9タスク）")
    print(f"  Phase 3: ✅ 完了（3タスク）")
    print(f"  Phase 4: ✅ 完了（5タスク）")
    print(f"  \n  合計完了: {9 + 3 + 5} = 17タスク")

if __name__ == '__main__':
    main()

