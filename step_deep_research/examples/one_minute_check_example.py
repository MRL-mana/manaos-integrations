#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1分チェックの実行例
"""

import sys
from pathlib import Path

# 1分チェックスクリプトをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from step_deep_research.one_minute_check import one_minute_check


if __name__ == "__main__":
    print("Step-Deep-Research 1分チェック実行")
    print("=" * 60)
    
    success = one_minute_check()
    
    if success:
        print("\n🎉 すべてのチェックが合格！完成状態です！")
        sys.exit(0)
    else:
        print("\n⚠️  一部のチェックが不合格。確認が必要です。")
        sys.exit(1)

