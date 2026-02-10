#!/usr/bin/env python3
"""
Phase1 ON N往復テスト。PHASE1_REFLECTION=on で API 起動していること。
Usage: python phase1_run_on_rounds.py [--rounds N]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests が必要です: pip install requests", file=sys.stderr)
    sys.exit(1)

API_URL = os.environ.get("PHASE1_API_URL", "http://localhost:9500")
CHAT_URL = f"{API_URL}/api/llm/chat"
TIMEOUT = int(os.environ.get("PHASE1_API_TIMEOUT", "300"))


def chat(messages: list, thread_id: str | None = None) -> dict:
    body = {"messages": messages}
    if thread_id:
        body["thread_id"] = thread_id
    r = requests.post(CHAT_URL, json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _extract_assistant_text(resp: dict) -> str:
    text = (resp.get("response") or "").strip()
    if text:
        return text
    msg = resp.get("message") or {}
    return (msg.get("content") or "").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=15)
    args = parser.parse_args()
    rounds = args.rounds

    print(f"=== Phase1 ON {rounds}-round test ===\n")
    thread_id = None
    history = []

    for i in range(1, rounds + 1):
        user_msg = f"Round {i}. What can you help me with?"
        history.append({"role": "user", "content": user_msg})
        print(f"[{i}/{rounds}] user: {user_msg}")
        try:
            resp = chat(history, thread_id)
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}", file=sys.stderr)
            sys.exit(1)
        assistant_text = _extract_assistant_text(resp)
        history.append({"role": "assistant", "content": assistant_text})
        thread_id = resp.get("thread_id") or thread_id
        short = assistant_text[:40] + "..." if len(assistant_text) > 40 else assistant_text
        print(f"         assistant: {short}")

    print("\n--- Aggregate (phase1_aggregate.py) ---\n")
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(root / "phase1_aggregate.py")], cwd=root)


if __name__ == "__main__":
    main()
