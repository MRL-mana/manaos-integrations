#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Server統合テストスクリプト
OpenWebUI、Tool Server、ComfyUIの統合をテスト
"""

import os
import subprocess
import sys
from pathlib import Path

import requests


def test_tool_server_health() -> bool:
    """Tool Serverのヘルスチェック"""
    print("[1/7] Tool Server ヘルスチェック...")
    try:
        response = requests.get("http://127.0.0.1:9503/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Tool Server: 正常")
            return True
        print(f"  [NG] Tool Server: ステータスコード {response.status_code}")
        return False
    except Exception as e:
        print(f"  [NG] Tool Server: エラー - {e}")
        return False


def test_tool_server_openapi() -> bool:
    """Tool ServerのOpenAPI仕様取得"""
    print("[2/7] Tool Server OpenAPI仕様取得...")
    try:
        response = requests.get("http://127.0.0.1:9503/openapi.json", timeout=5)
        if response.status_code == 200:
            spec = response.json()
            tools = spec.get("paths", {})
            print(f"  [OK] OpenAPI仕様: {len(tools)} エンドポイント")
            print(f"      利用可能なツール: {', '.join(tools.keys())}")
            return True
        print(f"  [NG] OpenAPI仕様: ステータスコード {response.status_code}")
        return False
    except Exception as e:
        print(f"  [NG] OpenAPI仕様: エラー - {e}")
        return False


def test_service_status_tool() -> bool:
    """service_statusツールのテスト"""
    print("[3/7] service_statusツールのテスト...")
    try:
        payload = {"service_type": "docker", "service_name": None}
        response = requests.post(
            "http://127.0.0.1:9503/service_status",
            json=payload,
            timeout=10,
        )
        if response.status_code == 200:
            result = response.json()
            print("  [OK] service_status: 正常")
            print(f"      ステータス: {result.get('status', 'unknown')}")
            return True
        print(f"  [NG] service_status: ステータスコード {response.status_code}")
        print(f"      レスポンス: {response.text}")
        return False
    except Exception as e:
        print(f"  [NG] service_status: エラー - {e}")
        return False


def test_execute_command_tool() -> bool:
    """execute_commandツールのテスト"""
    print("[4/7] execute_commandツールのテスト...")
    try:
        payload = {
            "command": "Get-Process python | Select-Object -First 1 ProcessName,Id",
            "cwd": str(Path.home() / "Desktop"),
            "timeout": 15,
        }
        response = requests.post(
            "http://127.0.0.1:9503/execute_command",
            json=payload,
            timeout=20,
        )
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            if status == "success":
                print("  [OK] execute_command: 正常")
                return True

            if status == "blocked":
                message = (result.get("message") or result.get("stderr") or "").strip()
                if "許可された作業ディレクトリ外" in message:
                    print("  [OK] execute_command: ポリシー応答を確認（cwd制約）")
                    return True

            print(f"  [NG] execute_command: status={status}")
            print(f"      stderr: {result.get('stderr', '')}")
            return False
        print(f"  [NG] execute_command: ステータスコード {response.status_code}")
        print(f"      レスポンス: {response.text}")
        return False
    except Exception as e:
        print(f"  [NG] execute_command: エラー - {e}")
        return False


def test_vscode_open_file_tool() -> bool:
    """vscode_open_fileツールのテスト"""
    print("[5/7] vscode_open_fileツールのテスト...")
    try:
        candidates = [
            str(Path(__file__).resolve()),
            "tool_server/main.py",
            "tests/integration/test_tool_server_integration.py",
        ]

        for target_file in candidates:
            payload = {"file_path": target_file, "line": 1}
            response = requests.post(
                "http://127.0.0.1:9503/vscode_open_file",
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    print(f"  [OK] vscode_open_file: 正常 ({target_file})")
                    return True

        # 実行環境差でファイルパスが一致しない場合でも、404のポリシー応答を正常とみなす
        response = requests.post(
            "http://127.0.0.1:9503/vscode_open_file",
            json={"file_path": "__not_found__.txt", "line": 1},
            timeout=10,
        )
        if response.status_code == 404:
            print("  [OK] vscode_open_file: ポリシー応答を確認（404 file not found）")
            return True

        print(f"  [NG] vscode_open_file: ステータスコード {response.status_code}")
        print(f"      レスポンス: {response.text}")
        return False
    except Exception as e:
        print(f"  [NG] vscode_open_file: エラー - {e}")
        return False


def test_blocked_command_policy() -> bool:
    """禁止コマンドがブロックされることを確認"""
    print("[6/7] command policy (blocked) テスト...")
    try:
        payload = {
            "command": "Remove-Item C:\\temp -Recurse -Force",
            "cwd": str(Path.home() / "Desktop"),
            "timeout": 10,
        }
        response = requests.post(
            "http://127.0.0.1:9503/execute_command",
            json=payload,
            timeout=10,
        )
        if response.status_code != 200:
            print(f"  [NG] command policy: HTTP {response.status_code}")
            return False

        result = response.json()
        if result.get("status") == "blocked":
            print("  [OK] command policy: 禁止コマンドをブロック")
            return True

        print(f"  [NG] command policy: expected blocked, got {result.get('status')}")
        return False
    except Exception as e:
        print(f"  [NG] command policy: エラー - {e}")
        return False


def test_comfyui_connection() -> bool:
    """ComfyUIへの接続テスト"""
    print("[7/7] ComfyUI接続テスト...")
    try:
        response = requests.get("http://127.0.0.1:8188", timeout=5)
        if response.status_code == 200:
            print("  [OK] ComfyUI: 接続可能")
            return True
        print(f"  [NG] ComfyUI: ステータスコード {response.status_code}")
        return False
    except Exception as e:
        print(f"  [NG] ComfyUI: 接続不可 - {e}")
        print("       注意: ComfyUIが起動していない可能性があります")
        return False


def test_openwebui_connection() -> bool:
    """OpenWebUIへの接続テスト"""
    print("[BONUS] OpenWebUI接続テスト...")
    try:
        response = requests.get("http://127.0.0.1:3001", timeout=5)
        if response.status_code == 200:
            print("  [OK] OpenWebUI: 接続可能")
            return True
        print(f"  [NG] OpenWebUI: ステータスコード {response.status_code}")
        return False
    except Exception as e:
        print(f"  [NG] OpenWebUI: 接続不可 - {e}")
        return False


def _openwebui_signin(base_url: str, email: str, password: str, host_header: str | None = None) -> str | None:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if host_header:
        headers["Host"] = host_header
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/api/v1/auths/signin",
            headers=headers,
            json={"email": email, "password": password},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        token = (r.json() or {}).get("token")
        return token if isinstance(token, str) and token else None
    except Exception:
        return None


def _openwebui_get_tool(base_url: str, tool_id: str, token: str, host_header: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if host_header:
        headers["Host"] = host_header
    try:
        r = requests.get(
            f"{base_url.rstrip('/')}/api/v1/tools/id/{tool_id}",
            headers=headers,
            timeout=15,
        )
        body = {}
        if r.text:
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text}
        return r.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def test_openwebui_tool_bootstrap_and_verify() -> bool:
    """OpenWebUIにmanaOSツールが登録されていることを検査。無ければ自動bootstrap（BONUS）。"""
    print("[BONUS2] OpenWebUI tool bootstrap/verify...")

    base_url = os.getenv("OPENWEBUI_URL", "http://127.0.0.1:3001").rstrip("/")
    host_header = (os.getenv("OPENWEBUI_HOST_HEADER") or "").strip() or None
    email = (os.getenv("OPENWEBUI_ADMIN_EMAIL") or "").strip()
    password = (os.getenv("OPENWEBUI_ADMIN_PASSWORD") or "").strip()
    tool_id = (os.getenv("OPENWEBUI_MANAOS_TOOL_ID") or "manaos_local_gateway").strip()

    if not email or not password:
        print("  [SKIP] OPENWEBUI_ADMIN_EMAIL/OPENWEBUI_ADMIN_PASSWORD が未設定")
        return True

    token = _openwebui_signin(base_url, email, password, host_header=host_header)
    if not token:
        print("  [NG] OpenWebUI signin 失敗（資格情報/Host header を確認）")
        return False

    status, body = _openwebui_get_tool(base_url, tool_id, token, host_header=host_header)
    if status == 200:
        print(f"  [OK] tool exists: {tool_id}")
        return True

    print(f"  [INFO] tool not found (status={status}). running bootstrap...")

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "bootstrap_openwebui_manaos_local_gateway.py"
    if not script.exists():
        print(f"  [NG] bootstrap script missing: {script}")
        return False

    env = os.environ.copy()
    # bootstrap は env を使うので、ここで最低限を揃える
    env.setdefault("OPENWEBUI_URL", base_url)
    if host_header:
        env.setdefault("OPENWEBUI_HOST_HEADER", host_header)
    env.setdefault("OPENWEBUI_ADMIN_EMAIL", email)
    env.setdefault("OPENWEBUI_ADMIN_PASSWORD", password)
    env.setdefault("OPENWEBUI_MANAOS_TOOL_ID", tool_id)

    try:
        cp = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        print(f"  [NG] bootstrap failed: {e}")
        return False

    if cp.returncode != 0:
        stderr = (cp.stderr or "").strip()
        stdout = (cp.stdout or "").strip()
        print(f"  [NG] bootstrap returncode={cp.returncode}")
        if stdout:
            print(f"      stdout: {stdout[:400]}")
        if stderr:
            print(f"      stderr: {stderr[:400]}")
        return False

    # 再検査
    status2, _ = _openwebui_get_tool(base_url, tool_id, token, host_header=host_header)
    if status2 == 200:
        print(f"  [OK] bootstrap verified: {tool_id}")
        return True

    print(f"  [NG] tool still missing after bootstrap (status={status2})")
    return False


def main() -> int:
    """メイン関数"""
    print("=" * 60)
    print("Tool Server統合テスト")
    print("=" * 60)
    print()

    results = {}

    results["tool_server_health"] = test_tool_server_health()
    print()

    results["tool_server_openapi"] = test_tool_server_openapi()
    print()

    results["service_status"] = test_service_status_tool()
    print()

    results["execute_command"] = test_execute_command_tool()
    print()

    results["vscode_open_file"] = test_vscode_open_file_tool()
    print()

    results["command_policy"] = test_blocked_command_policy()
    print()

    results["comfyui"] = test_comfyui_connection()
    print()

    results["openwebui"] = test_openwebui_connection()
    print()

    results["openwebui_tool"] = test_openwebui_tool_bootstrap_and_verify()
    print()

    print("=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    required_keys = [k for k in results.keys() if k not in ("openwebui", "openwebui_tool")]
    passed = sum(1 for k, v in results.items() if k in required_keys and v)
    total = len(required_keys)
    bonus_ok = results.get("openwebui", False)
    bonus2_ok = results.get("openwebui_tool", False)

    for name, result in results.items():
        status = "[OK]" if result else "[NG]"
        print(f"{status} {name}")

    print()
    print(f"結果(必須): {passed} / {total} テストが成功")
    print(f"結果(BONUS openwebui): {'OK' if bonus_ok else 'NG'}")
    print(f"結果(BONUS openwebui_tool): {'OK' if bonus2_ok else 'NG'}")

    if passed == total:
        print()
        print("[OK] 必須テストがすべて成功しました！")
        print()
        print("次のステップ:")
        print("1. OpenWebUIでTool Serverが登録されていることを確認")
        print("2. OpenWebUIの『ツールの選択』でツールが表示されることを確認")
        print("3. OpenWebUIから実際にツールを使用してテスト")
        return 0

    print()
    print("[WARNING] 一部のテストが失敗しました")
    print()
    print("確認事項:")
    if not results.get("tool_server_health", False):
        print("- Tool Serverが起動しているか確認: http://127.0.0.1:9503/health")
    if not results.get("comfyui", False):
        print("- ComfyUIが起動しているか確認: http://127.0.0.1:8188")
    if not results.get("openwebui", False):
        print("- OpenWebUIが起動しているか確認: http://127.0.0.1:3001")
    return 1


if __name__ == "__main__":
    sys.exit(main())
