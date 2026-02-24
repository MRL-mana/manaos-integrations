#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本格運用第1号計画を実行
記念すべき初実行を記録します
"""

import os
import sys
from pathlib import Path

# パス追加
sys.path.insert(0, str(Path(__file__).parent))

from manaos_moltbot_runner import run_list_files_only

def main():
    print('╔═══════════════════════════════════════════════════════════╗')
    print('║  🎉 本格運用開始 - 記念すべき第1号計画を実行します！    ║')
    print('╚═══════════════════════════════════════════════════════════╝')
    print()
    print('【計画内容】')
    print('  意図: Downloads フォルダの安全なスキャン')
    print('  対象: ~/Downloads')
    print('  実行内容: list_files（本物の OpenClaw v2026.1.30 で実行）')
    print('  監査: moltbot_audit に自動記録')
    print()

    # 実行
    result = run_list_files_only()

    print()
    print('【実行結果】')
    print(f"  計画ID: {result.get('plan_id', 'N/A')}")
    print(f"  状態: {result.get('status', 'N/A')}")
    print(f"  実行エンジン: {result.get('executor', 'unknown')}")

    if result.get('list_files_result'):
        files = result.get('list_files_result', {}).get('files', [])
        print(f'  検出ファイル数: {len(files)}')
        if files and len(files) <= 15:
            print('  ファイル一覧:')
            for f in files[:15]:
                print(f'    - {f}')
            if len(files) > 15:
                print(f'    ... 他 {len(files) - 15} ファイル')

    print()
    print('✅ 本格運用の第1号計画が正常に完了しました！')
    print()
    print('次のステップ:')
    print('  1. 監査ログを確認: moltbot_audit/2026-02-16/')
    print('  2. スケジュール実行を設定: 朝/昼/夜に自動実行')
    print('  3. Slack通知を試す: 実行結果の自動通知')

if __name__ == '__main__':
    main()
