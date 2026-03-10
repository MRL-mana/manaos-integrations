#!/usr/bin/env python3
"""
フェーズ1 OFF 3往復テスト。/api/llm/chat を3回叩き、thread_id を維持。
その後 phase1_aggregate.py を実行して集計結果を表示する。

手順:
  1. 別ターミナルで API を起動（OFFログ記録のため PHASE1_REFLECTION=off）:
       set PHASE1_REFLECTION=off   (※ Linux/mac は export)
       python unified_api_server.py
  2. このスクリプトを実行:
       python phase1_run_off_3rounds.py
  3. 出た集計全文を貼り付けて判定用に使う。
"""
import os
import subprocess
import sys
from pathlib import Path

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

# NOTE:
# このスクリプト内で PHASE1_REFLECTION を変更しても「サーバープロセス」には影響しない。
# OFF条件のログを取りたい場合は、サーバー起動側で PHASE1_REFLECTION=off を設定すること。

try:
    import requests
except ImportError:
    print("requests が必要です: pip install requests")
    sys.exit(1)

API_URL = os.environ.get("PHASE1_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
CHAT_URL = f"{API_URL}/api/llm/chat"
TIMEOUT = int(os.environ.get("PHASE1_API_TIMEOUT", "120"))


def chat(messages: list, thread_id: str | None = None) -> dict:
    body = {"messages": messages}
    if thread_id:
        body["thread_id"] = thread_id  # type: ignore
    r = requests.post(CHAT_URL, json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _extract_assistant_text(resp: dict) -> str:
    # unified_api_server/llm_routing は `response` を返す想定だが、互換で `message.content` も見る
    text = (resp.get("response") or "").strip()
    if text:
        return text
    msg = resp.get("message") or {}
    return (msg.get("content") or "").strip()


def main():
    print("=== Phase1 OFF 3往復テスト ===\n")
    thread_id = None
    history = []

    for i in range(1, 4):
        user_msg = f"テスト{i}回目です。"
        history.append({"role": "user", "content": user_msg})
        print(f"[Round {i}] user: {user_msg[:30]}...")
        try:
            resp = chat(history, thread_id)
        except requests.exceptions.RequestException as e:
            print(f"API エラー: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  status: {e.response.status_code}, body: {e.response.text[:500]}")
            print("\n※ unified_api_server が起動しているか確認してください。")
            sys.exit(1)
        assistant_text = _extract_assistant_text(resp)
        history.append({"role": "assistant", "content": assistant_text})
        thread_id = resp.get("thread_id") or thread_id
        turn_id = resp.get("turn_id")
        request_id = resp.get("request_id")
        print(f"         assistant: {assistant_text[:50]}...")
        print(
            f"         thread_id={thread_id[:8] if thread_id else '?'}..."
            f" turn_id={turn_id if turn_id is not None else '?'}"
            f" request_id={request_id[:8] if isinstance(request_id, str) else '?'}..."
        )

    print("\n--- 集計 (phase1_aggregate.py) ---\n")
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(root / "phase1_aggregate.py")], cwd=root)


if __name__ == "__main__":
    main()
