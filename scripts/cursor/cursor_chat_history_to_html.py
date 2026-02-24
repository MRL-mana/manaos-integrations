#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""チャット履歴を cursor_chat_history.html に出力するだけのスクリプト"""
import sys
from pathlib import Path

def main():
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    
    from cursor_chat_history_unified_viewer import CursorChatHistoryViewer
    
    out = script_dir / "cursor_chat_history.html"
    v = CursorChatHistoryViewer()
    v.scan_all_workspaces()
    v.export_to_html(out)
    print("OK:", out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
