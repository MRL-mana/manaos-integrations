#!/usr/bin/env python3
"""
重複・不要タスクのクリーンアップ
"""
import sys
sys.path.insert(0, '/root/trinity_workspace')
from core.db_manager import DatabaseManager
from datetime import datetime

db = DatabaseManager()

print('🧹 Trinity タスククリーンアップ')
print('=' * 60)

# 全タスクを取得
all_tasks = db.get_tasks()
print(f'クリーンアップ前: {len(all_tasks)}件\n')

# クリーンアップ対象
cleanup_targets = []

for task in all_tasks:
    task_id = task['id']
    
    # AUTO-で始まる自動生成タスク
    if task_id.startswith('AUTO-'):
        cleanup_targets.append(task)
    
    # TEST-で始まるテストタスク（完了済みのみ）
    elif task_id.startswith('TEST-') and task['status'] == 'done':
        cleanup_targets.append(task)

print(f'クリーンアップ対象: {len(cleanup_targets)}件')
print()

# 確認
if cleanup_targets:
    print('削除するタスク（最初の10件）:')
    for i, task in enumerate(cleanup_targets[:10]):
        print(f'  {i+1}. {task["id"]}: {task["title"][:50]}')
    
    if len(cleanup_targets) > 10:
        print(f'  ... 他 {len(cleanup_targets) - 10}件')
    
    print()
    
    # 削除実行
    deleted = 0
    for task in cleanup_targets:
        try:
            db.delete_task(task['id'])
            deleted += 1
        except Exception as e:
            print(f'❌ {task["id"]}: {e}')
    
    print(f'✅ {deleted}件のタスクを削除しました')
else:
    print('✅ クリーンアップ不要（重複タスクなし）')

print()

# 最終状態
remaining_tasks = db.get_tasks()
print(f'クリーンアップ後: {len(remaining_tasks)}件')
print()

# ステータス集計
status_counts = {}
for task in remaining_tasks:
    status = task['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print('ステータス別:')
for status, count in sorted(status_counts.items()):
    icon = {'todo': '📝', 'in_progress': '🔄', 'review': '👀', 'done': '✅', 'blocked': '🚫'}.get(status, '❓')
    print(f'  {icon} {status:15s}: {count:3d}件')

print()
print('=' * 60)

