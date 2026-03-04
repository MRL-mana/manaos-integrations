#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mana Tasks CLI - Mana専用タスク管理コマンドラインツール
====================================================

機能:
- タスクの表示・作成・編集・削除
- 高度な検索・フィルタリング
- タスクエクスポート（JSON/CSV/Markdown）
- タスク統計・分析
- インタラクティブモード

Author: Luna (Trinity Implementation AI)
Created: 2025-10-18
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import click
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from tabulate import tabulate
from core.db_manager import DatabaseManager

# カラー定義
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ===== ユーティリティ関数 =====

def colorize(text: str, color: str) -> str:
    """テキストに色を付ける"""
    return f"{color}{text}{Colors.ENDC}"


def format_priority(priority: str) -> str:
    """優先度をカラーで表示"""
    priority_colors = {
        'urgent': Colors.FAIL,
        'high': Colors.WARNING,
        'medium': Colors.OKBLUE,
        'low': Colors.OKCYAN
    }
    color = priority_colors.get(priority, '')
    return colorize(priority.upper(), color)


def format_status(status: str) -> str:
    """ステータスをアイコン付きで表示"""
    status_icons = {
        'todo': '📝',
        'in_progress': '🔄',
        'review': '👀',
        'done': '✅',
        'blocked': '🚫'
    }
    icon = status_icons.get(status, '❓')
    return f"{icon} {status}"


def format_agent(agent: str) -> str:
    """エージェント名をアイコン付きで表示"""
    agent_icons = {
        'Remi': '🎯',
        'Luna': '🌙',
        'Mina': '🔍',
        'Aria': '📖'
    }
    icon = agent_icons.get(agent, '👤')
    return f"{icon} {agent}"


# ===== メインCLI =====

@click.group()
@click.version_option(version='2.0', prog_name='Mana Tasks CLI')
def cli():
    """
    🎯 Mana Tasks CLI - Trinity v2.0 タスク管理ツール
    
    Mana専用のタスク管理コマンドラインインターフェース
    """
    pass


# ===== リスト表示 =====

@cli.command(name='list')
@click.option('--status', '-s', type=click.Choice(['todo', 'in_progress', 'review', 'done', 'blocked']), help='ステータスでフィルタ')
@click.option('--agent', '-a', type=click.Choice(['Remi', 'Luna', 'Mina', 'Aria']), help='担当者でフィルタ')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']), help='優先度でフィルタ')
@click.option('--limit', '-l', type=int, default=50, help='表示件数')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'simple']), default='table', help='出力フォーマット')
def list_tasks(status, agent, priority, limit, format):
    """タスク一覧を表示"""
    
    db = DatabaseManager()
    tasks = db.get_tasks(status=status, assigned_to=agent, priority=priority)
    tasks = tasks[:limit]
    
    if not tasks:
        click.echo(colorize("📭 タスクが見つかりませんでした", Colors.WARNING))
        return
    
    if format == 'json':
        click.echo(json.dumps(tasks, ensure_ascii=False, indent=2))
        return
    
    if format == 'simple':
        for task in tasks:
            click.echo(f"{task['id']}: {task['title']} ({task['status']})")
        return
    
    # テーブル表示
    table_data = []
    for task in tasks:
        table_data.append([
            task['id'],
            task['title'][:40],
            format_status(task['status']),
            format_priority(task.get('priority', 'medium')),
            format_agent(task.get('assigned_to', '-')),
            task.get('estimated_hours', '-')
        ])
    
    headers = ['ID', 'Title', 'Status', 'Priority', 'Assigned', 'Hours']
    
    click.echo()
    click.echo(colorize(f"📋 Tasks ({len(tasks)} items)", Colors.BOLD))
    click.echo()
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
    click.echo()


# ===== タスク詳細 =====

@cli.command(name='show')
@click.argument('task_id')
def show_task(task_id):
    """タスク詳細を表示"""
    
    db = DatabaseManager()
    tasks = db.get_tasks(task_id=task_id)
    
    if not tasks:
        click.echo(colorize(f"❌ タスク {task_id} が見つかりません", Colors.FAIL))
        return
    
    task = tasks[0]
    
    click.echo()
    click.echo(colorize(f"📋 Task Details: {task['id']}", Colors.BOLD))
    click.echo("=" * 60)
    click.echo()
    
    # 基本情報
    click.echo(colorize("基本情報:", Colors.OKBLUE))
    click.echo(f"  タイトル: {task['title']}")
    click.echo(f"  ステータス: {format_status(task['status'])}")
    click.echo(f"  優先度: {format_priority(task.get('priority', 'medium'))}")
    click.echo(f"  担当者: {format_agent(task.get('assigned_to', '-'))}")
    click.echo()
    
    # 時間情報
    click.echo(colorize("時間情報:", Colors.OKBLUE))
    click.echo(f"  作成日時: {task.get('created_at', '-')}")
    click.echo(f"  更新日時: {task.get('updated_at', '-')}")
    if task.get('completed_at'):
        click.echo(f"  完了日時: {task['completed_at']}")
    click.echo(f"  予定時間: {task.get('estimated_hours', '-')}h")
    if task.get('actual_hours'):
        click.echo(f"  実績時間: {task['actual_hours']}h")
    click.echo()
    
    # 説明・ノート
    if task.get('description'):
        click.echo(colorize("説明:", Colors.OKBLUE))
        click.echo(f"  {task['description']}")
        click.echo()
    
    if task.get('notes'):
        click.echo(colorize("ノート:", Colors.OKBLUE))
        click.echo(f"  {task['notes']}")
        click.echo()
    
    # 依存関係
    if task.get('dependencies'):
        deps = json.loads(task['dependencies']) if isinstance(task['dependencies'], str) else task['dependencies']
        if deps:
            click.echo(colorize("依存タスク:", Colors.OKBLUE))
            for dep in deps:
                click.echo(f"  - {dep}")
            click.echo()
    
    # タグ
    if task.get('tags'):
        tags = json.loads(task['tags']) if isinstance(task['tags'], str) else task['tags']
        if tags:
            click.echo(colorize("タグ:", Colors.OKBLUE))
            tag_str = ', '.join([f"#{tag}" for tag in tags])
            click.echo(f"  {tag_str}")
            click.echo()


# ===== タスク作成 =====

@cli.command(name='create')
@click.option('--title', '-t', required=True, help='タスクタイトル')
@click.option('--status', '-s', type=click.Choice(['todo', 'in_progress', 'review', 'done', 'blocked']), default='todo', help='ステータス')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']), default='medium', help='優先度')
@click.option('--agent', '-a', type=click.Choice(['Remi', 'Luna', 'Mina', 'Aria']), help='担当者')
@click.option('--hours', '-h', type=float, help='予定時間（時間）')
@click.option('--description', '-d', help='説明')
def create_task(title, status, priority, agent, hours, description):
    """新規タスクを作成"""
    
    db = DatabaseManager()
    
    # タスクデータ作成
    task_data = {
        'title': title,
        'status': status,
        'priority': priority,
        'created_by': 'Mana',
        'description': description
    }
    
    if agent:
        task_data['assigned_to'] = agent
    
    if hours:
        task_data['estimated_hours'] = hours
    
    # タスク作成
    task_id = db.create_task(task_data)
    
    click.echo()
    click.echo(colorize(f"✅ タスク作成完了: {task_id}", Colors.OKGREEN))
    click.echo(f"   タイトル: {title}")
    click.echo(f"   優先度: {priority}")
    if agent:
        click.echo(f"   担当者: {agent}")
    click.echo()


# ===== タスク編集 =====

@cli.command(name='edit')
@click.argument('task_id')
@click.option('--title', '-t', help='タイトル')
@click.option('--status', '-s', type=click.Choice(['todo', 'in_progress', 'review', 'done', 'blocked']), help='ステータス')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']), help='優先度')
@click.option('--agent', '-a', type=click.Choice(['Remi', 'Luna', 'Mina', 'Aria']), help='担当者')
@click.option('--hours', '-h', type=float, help='予定時間（時間）')
@click.option('--notes', '-n', help='ノート')
def edit_task(task_id, title, status, priority, agent, hours, notes):
    """タスクを編集"""
    
    db = DatabaseManager()
    
    # タスク存在確認
    tasks = db.get_tasks(task_id=task_id)
    if not tasks:
        click.echo(colorize(f"❌ タスク {task_id} が見つかりません", Colors.FAIL))
        return
    
    # 更新データ作成
    updates = {}
    
    if title:
        updates['title'] = title
    if status:
        updates['status'] = status
    if priority:
        updates['priority'] = priority
    if agent:
        updates['assigned_to'] = agent
    if hours is not None:
        updates['estimated_hours'] = hours
    if notes:
        updates['notes'] = notes
    
    if not updates:
        click.echo(colorize("⚠️  更新項目が指定されていません", Colors.WARNING))
        return
    
    # タスク更新
    db.update_task(task_id, updates)
    
    click.echo()
    click.echo(colorize(f"✅ タスク更新完了: {task_id}", Colors.OKGREEN))
    for key, value in updates.items():
        click.echo(f"   {key}: {value}")
    click.echo()


# ===== タスク削除 =====

@cli.command(name='delete')
@click.argument('task_id')
@click.confirmation_option(prompt='本当に削除しますか？')
def delete_task(task_id):
    """タスクを削除"""
    
    db = DatabaseManager()
    
    # タスク存在確認
    tasks = db.get_tasks(task_id=task_id)
    if not tasks:
        click.echo(colorize(f"❌ タスク {task_id} が見つかりません", Colors.FAIL))
        return
    
    # タスク削除
    db.delete_task(task_id)
    
    click.echo()
    click.echo(colorize(f"✅ タスク削除完了: {task_id}", Colors.OKGREEN))
    click.echo()


# ===== 検索 =====

@cli.command(name='search')
@click.argument('query')
@click.option('--limit', '-l', type=int, default=20, help='表示件数')
def search_tasks(query, limit):
    """タスクを検索（タイトル・説明・ノートから）"""
    
    db = DatabaseManager()
    
    # 全タスク取得
    all_tasks = db.get_tasks()
    
    # 検索
    query_lower = query.lower()
    results = []
    
    for task in all_tasks:
        # タイトル、説明、ノートから検索
        if (query_lower in task['title'].lower() or
            (task.get('description') and query_lower in task['description'].lower()) or
            (task.get('notes') and query_lower in task['notes'].lower())):
            results.append(task)
    
    results = results[:limit]
    
    if not results:
        click.echo(colorize(f"📭 「{query}」に一致するタスクが見つかりませんでした", Colors.WARNING))
        return
    
    # テーブル表示
    table_data = []
    for task in results:
        table_data.append([
            task['id'],
            task['title'][:40],
            format_status(task['status']),
            format_agent(task.get('assigned_to', '-'))
        ])
    
    headers = ['ID', 'Title', 'Status', 'Assigned']
    
    click.echo()
    click.echo(colorize(f"🔍 Search Results: 「{query}」 ({len(results)} items)", Colors.BOLD))
    click.echo()
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
    click.echo()


# ===== 統計 =====

@cli.command(name='stats')
def show_stats():
    """タスク統計を表示"""
    
    db = DatabaseManager()
    stats = db.get_task_stats()
    
    click.echo()
    click.echo(colorize("📊 Task Statistics", Colors.BOLD))
    click.echo("=" * 60)
    click.echo()
    
    # 全体統計
    click.echo(colorize("全体統計:", Colors.OKBLUE))
    click.echo(f"  総タスク数: {stats['total_tasks']}")
    click.echo()
    
    # ステータス別
    click.echo(colorize("ステータス別:", Colors.OKBLUE))
    for status, count in stats['by_status'].items():
        click.echo(f"  {format_status(status)}: {count}")
    click.echo()
    
    # 優先度別
    click.echo(colorize("優先度別:", Colors.OKBLUE))
    for priority, count in stats['by_priority'].items():
        click.echo(f"  {format_priority(priority)}: {count}")
    click.echo()
    
    # 担当者別
    click.echo(colorize("担当者別:", Colors.OKBLUE))
    for agent, count in stats['by_agent'].items():
        click.echo(f"  {format_agent(agent)}: {count}")
    click.echo()
    
    # 完了率
    if stats['total_tasks'] > 0:
        completion_rate = (stats['by_status'].get('done', 0) / stats['total_tasks']) * 100
        click.echo(colorize("完了率:", Colors.OKBLUE))
        click.echo(f"  {completion_rate:.1f}%")
        click.echo()


# ===== エクスポート =====

@cli.command(name='export')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'markdown']), default='json', help='出力フォーマット')
@click.option('--output', '-o', type=click.Path(), help='出力ファイル（指定しない場合は標準出力）')
@click.option('--status', '-s', type=click.Choice(['todo', 'in_progress', 'review', 'done', 'blocked']), help='ステータスでフィルタ')
def export_tasks(format, output, status):
    """タスクをエクスポート"""
    
    db = DatabaseManager()
    tasks = db.get_tasks(status=status)
    
    if not tasks:
        click.echo(colorize("📭 タスクが見つかりませんでした", Colors.WARNING))
        return
    
    # フォーマット変換
    if format == 'json':
        content = json.dumps(tasks, ensure_ascii=False, indent=2)
    
    elif format == 'csv':
        import csv
        from io import StringIO
        
        output_io = StringIO()
        writer = csv.DictWriter(output_io, fieldnames=tasks[0].keys())
        writer.writeheader()
        writer.writerows(tasks)
        content = output_io.getvalue()
    
    elif format == 'markdown':
        content = f"# Trinity Tasks Export\n\n"
        content += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"Total Tasks: {len(tasks)}\n\n"
        content += "---\n\n"
        
        for task in tasks:
            content += f"## {task['id']}: {task['title']}\n\n"
            content += f"- **Status**: {task['status']}\n"
            content += f"- **Priority**: {task.get('priority', 'medium')}\n"
            content += f"- **Assigned**: {task.get('assigned_to', '-')}\n"
            content += f"- **Created**: {task.get('created_at', '-')}\n"
            
            if task.get('description'):
                content += f"\n{task['description']}\n"
            
            content += "\n---\n\n"
    
    # 出力
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        click.echo(colorize(f"✅ エクスポート完了: {output}", Colors.OKGREEN))
    else:
        click.echo(content)


# ===== メイン実行 =====

if __name__ == '__main__':
    cli()

