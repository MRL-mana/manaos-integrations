#!/usr/bin/env python3
"""
Mana専用タスク管理CLI - Trinity v2.0 デモ実装
Remi（戦略AI）→ Luna（実装AI）協調で作成
"""

import click
import json
from datetime import datetime
from pathlib import Path

# カラー定義
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

# タスクファイルパス
TASK_FILE = Path.home() / '.mana_tasks.json'

def load_tasks():
    """タスク読み込み"""
    if TASK_FILE.exists():
        with open(TASK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    """タスク保存"""
    with open(TASK_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

@click.group()
def cli():
    """🎯 Mana専用タスク管理CLI - Trinity v2.0製"""
    pass

@cli.command()
@click.argument('title')
@click.option('--priority', '-p', default='medium', type=click.Choice(['low', 'medium', 'high', 'urgent']))
@click.option('--due', '-d', default=None, help='期限（YYYY-MM-DD）')
def add(title, priority, due):
    """✨ タスク追加"""
    tasks = load_tasks()
    
    task = {
        'id': len(tasks) + 1,
        'title': title,
        'priority': priority,
        'status': 'todo',
        'created_at': datetime.now().isoformat(),
        'due_date': due
    }
    
    tasks.append(task)
    save_tasks(tasks)
    
    # 優先度に応じた色
    priority_colors = {
        'urgent': Colors.RED,
        'high': Colors.YELLOW,
        'medium': Colors.BLUE,
        'low': Colors.CYAN
    }
    
    color = priority_colors.get(priority, Colors.RESET)
    
    click.echo(f"\n{Colors.GREEN}✅ タスク追加成功！{Colors.RESET}")
    click.echo(f"{color}📋 [{task['id']}] {title} (優先度: {priority}){Colors.RESET}")
    if due:
        click.echo(f"   📅 期限: {due}")
    click.echo()

@cli.command()
@click.option('--status', '-s', default=None, type=click.Choice(['todo', 'done']))
@click.option('--priority', '-p', default=None, type=click.Choice(['low', 'medium', 'high', 'urgent']))
def list(status, priority):
    """📋 タスク一覧"""
    tasks = load_tasks()
    
    # フィルタ
    if status:
        tasks = [t for t in tasks if t['status'] == status]
    if priority:
        tasks = [t for t in tasks if t['priority'] == priority]
    
    if not tasks:
        click.echo(f"\n{Colors.YELLOW}⚠️ タスクがありません{Colors.RESET}\n")
        return
    
    # 統計
    total = len(load_tasks())
    done = len([t for t in load_tasks() if t['status'] == 'done'])
    todo = len([t for t in load_tasks() if t['status'] == 'todo'])
    
    click.echo(f"\n{Colors.BOLD}📊 Manaのタスク一覧{Colors.RESET}")
    click.echo(f"{Colors.CYAN}総タスク: {total}件 | ✅完了: {done}件 | 📋TODO: {todo}件{Colors.RESET}\n")
    click.echo("─" * 80)
    
    for task in tasks:
        # ステータスアイコン
        status_icon = '✅' if task['status'] == 'done' else '📋'
        
        # 優先度色
        priority_colors = {
            'urgent': Colors.RED,
            'high': Colors.YELLOW,
            'medium': Colors.BLUE,
            'low': Colors.CYAN
        }
        color = priority_colors.get(task['priority'], Colors.RESET)
        
        click.echo(f"{status_icon} [{color}{task['id']:3d}{Colors.RESET}] "
                   f"{Colors.BOLD}{task['title']}{Colors.RESET}")
        click.echo(f"      優先度: {color}{task['priority']:6s}{Colors.RESET}  "
                   f"作成: {task['created_at'][:10]}")
        
        if task.get('due_date'):
            click.echo(f"      📅 期限: {task['due_date']}")
        
        click.echo()

@cli.command()
@click.argument('task_id', type=int)
def done(task_id):
    """✅ タスク完了"""
    tasks = load_tasks()
    
    found = False
    for task in tasks:
        if task['id'] == task_id:
            if task['status'] == 'done':
                click.echo(f"\n{Colors.YELLOW}⚠️ タスク {task_id} は既に完了しています{Colors.RESET}\n")
                return
            
            task['status'] = 'done'
            task['completed_at'] = datetime.now().isoformat()
            found = True
            
            save_tasks(tasks)
            click.echo(f"\n{Colors.GREEN}🎉 タスク完了！{Colors.RESET}")
            click.echo(f"{Colors.BOLD}{task['title']}{Colors.RESET}\n")
            break
    
    if not found:
        click.echo(f"\n{Colors.RED}❌ タスク {task_id} が見つかりません{Colors.RESET}\n")

@cli.command()
@click.argument('task_id', type=int)
def delete(task_id):
    """🗑️ タスク削除"""
    tasks = load_tasks()
    
    original_count = len(tasks)
    tasks = [t for t in tasks if t['id'] != task_id]
    
    if len(tasks) < original_count:
        save_tasks(tasks)
        click.echo(f"\n{Colors.GREEN}✅ タスク {task_id} を削除しました{Colors.RESET}\n")
    else:
        click.echo(f"\n{Colors.RED}❌ タスク {task_id} が見つかりません{Colors.RESET}\n")

@cli.command()
def stats():
    """📊 統計情報"""
    tasks = load_tasks()
    
    if not tasks:
        click.echo(f"\n{Colors.YELLOW}⚠️ タスクがありません{Colors.RESET}\n")
        return
    
    total = len(tasks)
    done = len([t for t in tasks if t['status'] == 'done'])
    todo = len([t for t in tasks if t['status'] == 'todo'])
    
    # 優先度別
    by_priority = {'urgent': 0, 'high': 0, 'medium': 0, 'low': 0}
    for task in tasks:
        if task['status'] == 'todo':
            by_priority[task['priority']] += 1
    
    click.echo(f"\n{Colors.BOLD}📊 Manaのタスク統計{Colors.RESET}\n")
    click.echo(f"総タスク: {total}件")
    click.echo(f"✅ 完了: {Colors.GREEN}{done}件{Colors.RESET} ({done/total*100:.1f}%)")
    click.echo(f"📋 TODO: {Colors.YELLOW}{todo}件{Colors.RESET}")
    
    click.echo("\n優先度別（TODO）:")
    click.echo(f"  🔴 緊急: {by_priority['urgent']}件")
    click.echo(f"  🟡 高: {by_priority['high']}件")
    click.echo(f"  🔵 中: {by_priority['medium']}件")
    click.echo(f"  ⚪ 低: {by_priority['low']}件")
    click.echo()

@cli.command()
def today():
    """📅 今日のタスク"""
    tasks = load_tasks()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 期限が今日のタスク
    today_tasks = [t for t in tasks if t.get('due_date') == today_str and t['status'] == 'todo']
    
    # 期限切れタスク
    overdue = [t for t in tasks 
               if t.get('due_date') and t['due_date'] < today_str and t['status'] == 'todo']
    
    click.echo(f"\n{Colors.BOLD}📅 今日のタスク ({today_str}){Colors.RESET}\n")
    
    if overdue:
        click.echo(f"{Colors.RED}🚨 期限切れ: {len(overdue)}件{Colors.RESET}")
        for task in overdue[:3]:
            click.echo(f"  ⚠️ [{task['id']}] {task['title']} (期限: {task['due_date']})")
        click.echo()
    
    if today_tasks:
        click.echo(f"{Colors.YELLOW}📌 今日期限: {len(today_tasks)}件{Colors.RESET}")
        for task in today_tasks:
            click.echo(f"  🔔 [{task['id']}] {task['title']}")
        click.echo()
    else:
        click.echo(f"{Colors.GREEN}✨ 今日のタスクはありません{Colors.RESET}\n")

if __name__ == '__main__':
    cli()


