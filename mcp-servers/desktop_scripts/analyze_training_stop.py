# -*- coding: utf-8 -*-
"""訓練停止の原因を分析するスクリプト"""

import os
import sys
from pathlib import Path
from datetime import datetime
import re

def analyze_training_stop():
    """訓練停止の原因を分析"""
    log_file = Path("lora_training_log.txt")
    
    if not log_file.exists():
        print("ログファイルが見つかりません")
        return
    
    print("=" * 60)
    print("訓練停止原因分析")
    print("=" * 60)
    
    # ログを読み込み
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f"\nログファイル総行数: {len(lines)}")
    print(f"ファイルサイズ: {log_file.stat().st_size / 1024:.1f} KB")
    
    # 最終更新時刻
    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
    now = datetime.now()
    age_minutes = (now - mtime).total_seconds() / 60
    print(f"最終更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"経過時間: {age_minutes:.1f} 分前")
    
    # エラーパターンを検索
    error_patterns = [
        (r'error|Error|ERROR', 'エラー'),
        (r'exception|Exception|EXCEPTION', '例外'),
        (r'traceback|Traceback|TRACEBACK', 'トレースバック'),
        (r'failed|Failed|FAILED', '失敗'),
        (r'kill|Kill|KILL', '強制終了'),
        (r'terminated|Terminated|TERMINATED', '終了'),
        (r'out of memory|OOM|memory', 'メモリ不足'),
        (r'cuda|cuda error', 'CUDAエラー'),
        (r'connection|timeout', '接続エラー'),
    ]
    
    print("\n" + "=" * 60)
    print("エラーパターン検索")
    print("=" * 60)
    
    found_errors = False
    for pattern, desc in error_patterns:
        matches = []
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                matches.append((i+1, line.strip()))
        
        if matches:
            found_errors = True
            print(f"\n[{desc}] 見つかりました ({len(matches)}件):")
            for line_num, line_text in matches[-5:]:  # 最後の5件だけ表示
                print(f"  行 {line_num}: {line_text[:100]}")
    
    if not found_errors:
        print("\nエラーパターンは見つかりませんでした")
    
    # 最後の50行を表示
    print("\n" + "=" * 60)
    print("ログの最後の50行")
    print("=" * 60)
    for i, line in enumerate(lines[-50:], start=len(lines)-49):
        print(f"{i:5d}: {line.rstrip()}")
    
    # 推測される原因
    print("\n" + "=" * 60)
    print("推測される原因")
    print("=" * 60)
    
    if age_minutes > 15:
        print(f"1. 訓練プロセスが停止している可能性（{age_minutes:.1f}分間更新なし）")
    
    if not found_errors:
        print("2. エラーログが見つからないため、以下の可能性:")
        print("   - バックグラウンドプロセスが正常終了した")
        print("   - システムがプロセスを終了させた（メモリ不足など）")
        print("   - ユーザーが手動で終了した")
        print("   - ターミナルウィンドウが閉じられた")
    
    # 最終ステップ情報
    step_pattern = r'Steps:\s+\d+%\|\S+\|\s+(\d+)/(\d+)'
    last_step = None
    for line in reversed(lines):
        match = re.search(step_pattern, line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            last_step = (current, total)
            break
    
    if last_step:
        current, total = last_step
        print(f"\n3. 最終ステップ: {current}/{total} ({current/total*100:.1f}%)")
        print(f"   進捗: {current/total*100:.1f}% 完了")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_training_stop()
















