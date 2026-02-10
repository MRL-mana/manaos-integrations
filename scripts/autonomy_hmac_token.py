#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時間ベース HMAC Confirm Token を生成して標準出力に出力する。
Autonomy の confirm_token_hmac_secret と同じ秘密鍵を環境変数で指定すること。

使い方:
  set AUTONOMY_HMAC_SECRET=your_secret
  python scripts/autonomy_hmac_token.py

  # 窓を 600 秒にしたい場合
  set AUTONOMY_HMAC_WINDOW_SECONDS=600
  python scripts/autonomy_hmac_token.py
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))


def main():
    secret = os.environ.get("AUTONOMY_HMAC_SECRET", "").strip()
    if not secret:
        print("AUTONOMY_HMAC_SECRET を設定してください。", file=sys.stderr)
        sys.exit(1)
    window = int(os.environ.get("AUTONOMY_HMAC_WINDOW_SECONDS", "300"))
    try:
        from autonomy_gates import generate_hmac_confirm_token

        token = generate_hmac_confirm_token(secret, window_seconds=window)
        print(token)
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
