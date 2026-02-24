#!/usr/bin/env python3
"""
LTX-2動画生成を実行するスクリプト
ComfyUIにワークフローを送信し、完了まで待機して出力パスを表示します。

必要な環境:
  - ComfyUI が起動していること（既定: http://127.0.0.1:8188）
  - LTX-2用カスタムノード: ComfyUI-LTXVideo
    https://github.com/Lightricks/ComfyUI-LTXVideo
    ComfyUI Manager で "LTXVideo" を検索してインストール、または
    custom_nodes に git clone して ComfyUI を再起動
  - 開始画像を ComfyUI の input フォルダに配置（例: test_image.png）
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests


def load_workflow(path: str) -> dict:
    """ワークフローJSONを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fix_workflow_paths(workflow: dict) -> None:
    """Windows ComfyUI用: パス区切りを / から \\ に正規化（gemma_path 等）"""
    for node in workflow.values():
        if not isinstance(node, dict) or "inputs" not in node:
            continue
        for k, v in list(node["inputs"].items()):
            if (
                isinstance(v, str)
                and "/" in v
                and ("model" in v or "gemma" in v.lower() or ".safetensors" in v)
            ):
                node["inputs"][k] = v.replace("/", "\\")


def submit_workflow(base_url: str, workflow: dict, client_id: str = "run_ltx2") -> str | None:
    """ComfyUIにワークフローを送信し、prompt_idを返す"""
    url = f"{base_url.rstrip('/')}/prompt"
    payload = {"prompt": workflow, "client_id": client_id}
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code != 200:
            try:
                err = r.json()
                msg = err.get("error", {}).get("message", r.text) or r.text
                print(f"ComfyUIエラー ({r.status_code}): {msg}")
                if "does not exist" in str(msg):
                    print(
                        "ヒント: ComfyUIでワークフローを開き、File -> Export (API) で保存したJSONを使うと、利用中のノードに合います。"
                    )
            except Exception:
                print(f"送信エラー: {r.status_code} {r.text[:500]}")
            return None
        return r.json().get("prompt_id")
    except Exception as e:
        print(f"送信エラー: {e}")
        return None


def get_queue(base_url: str) -> dict:
    """キュー状態を取得"""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/queue", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_history_for_prompt(base_url: str, prompt_id: str) -> dict | None:
    """指定prompt_idの履歴（出力）を取得。戻り値は { prompt_id: { outputs: ... } } 形式に正規化"""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/history/{prompt_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
        # ComfyUIは /history/{id} でそのpromptの結果だけ返す場合がある
        if "outputs" in data and prompt_id not in data:
            return {prompt_id: data}
        return data
    except Exception as e:
        print(f"履歴取得エラー: {e}")
        return None


def wait_for_completion(
    base_url: str, prompt_id: str, poll_interval: float = 5.0, timeout: float = 600.0
) -> dict | None:
    """完了まで待機し、履歴を返す。タイムアウトまたはエラー時はNone"""
    start = time.time()
    while (time.time() - start) < timeout:
        queue = get_queue(base_url)
        if "error" in queue:
            print(f"キュー取得エラー: {queue['error']}")
            time.sleep(poll_interval)
            continue
        running = [x[0] for x in queue.get("queue_running", [])]
        pending = [x[0] for x in queue.get("queue_pending", [])]
        if prompt_id not in running and prompt_id not in pending:
            hist = get_history_for_prompt(base_url, prompt_id)
            if hist:
                return hist
            # 履歴にまだ出てこない場合少し待つ
            time.sleep(2.0)
            hist = get_history_for_prompt(base_url, prompt_id)
            if hist:
                return hist
            print("履歴に結果がまだありません。しばらく待って再試行してください。")
            return None
        print(f"  実行中... (経過 {int(time.time() - start)}s)")
        time.sleep(poll_interval)
    print("タイムアウトしました。")
    return None


def extract_output_paths(history: dict, prompt_id: str) -> list[tuple[str, str]]:
    """履歴から出力ファイル（動画）のサブフォルダとファイル名を抽出"""
    out = []
    if prompt_id not in history:
        return out
    outputs = history[prompt_id].get("outputs", {})
    for node_id, node_out in outputs.items():
        for key in ("videos", "gifs"):
            for item in node_out.get(key, []):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    subfolder, filename = item[0], item[1]
                    out.append((subfolder, filename))
        if "video" in node_out:
            v = node_out["video"]
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                out.append((v[0], v[1]))
    return out


def get_object_info(base_url: str) -> dict | None:
    """ComfyUI の /object_info を取得"""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return None


def collect_workflow_class_types(workflow: dict) -> set[str]:
    """API形式のワークフローから class_type を集める"""
    out = set()
    for node in workflow.values():
        if isinstance(node, dict) and "class_type" in node:
            out.add(node["class_type"])
    return out


def validate_workflow_nodes(base_url: str, workflow: dict) -> tuple[bool, list[str]] | None:
    """
    ワークフローで使われているノードが ComfyUI に存在するか検証する。
    戻り値: (OKか, 不足ノードのリスト)。接続失敗時は None。
    """
    obj = get_object_info(base_url)
    if not obj:
        return None
    available = set(obj.keys())
    used = collect_workflow_class_types(workflow)
    missing = sorted(used - available)
    return (len(missing) == 0, missing)


def check_comfyui(base_url: str) -> bool:
    """ComfyUI接続とLTX-2ノードの有無を確認"""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/system_stats", timeout=10)
        if r.status_code != 200:
            print(f"ComfyUI接続失敗: {r.status_code}")
            return False
        obj = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=10)
        if obj.status_code != 200:
            print("object_infoの取得に失敗しました")
            return False
        nodes = obj.json()
        # SaveVideo 必須。LTX系は現行名のいずれかがあればOK
        if "SaveVideo" not in nodes:
            missing = ["SaveVideo"]
        else:
            ltx_names = [
                "LowVRAMAudioVAELoader",
                "LTXVAudioVAELoader",
                "LTXVImgToVideo",
                "LTXVImgToVideoInplace",
            ]
            missing = [] if any(n in nodes for n in ltx_names) else ltx_names[:2]
        if missing:
            print("ComfyUIは接続できましたが、以下のLTX-2ノードがありません:")
            for n in missing:
                print(f"  - {n}")
            print(
                "ComfyUI-LTXVideo をインストールしてください: https://github.com/Lightricks/ComfyUI-LTXVideo"
            )
            return False
        print("ComfyUI接続OK。LTX-2用ノードも検出済みです。")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ComfyUIに接続できません: {e}")
        print("ComfyUIを起動し、--comfy-url でURLを指定してください。")
        return False


def main():
    parser = argparse.ArgumentParser(description="LTX-2動画生成をComfyUIで実行")
    parser.add_argument(
        "--comfy-url",
        default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"),
        help="ComfyUIのURL",
    )
    parser.add_argument(
        "--workflow",
        default=None,
        help="ワークフローJSONパス（未指定時は ltx2_workflow_debug.json）",
    )
    parser.add_argument("--prompt", default=None, help="プロンプト（上書き）")
    parser.add_argument(
        "--image", default=None, help="開始画像ファイル名（ComfyUIのinputフォルダ内）"
    )
    parser.add_argument("--no-wait", action="store_true", help="送信のみ行い待機しない")
    parser.add_argument("--timeout", type=float, default=600.0, help="完了待ちタイムアウト（秒）")
    parser.add_argument(
        "--check", action="store_true", help="ComfyUI接続とLTX-2ノードの有無のみ確認して終了"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="送信せず、ワークフローのノードがComfyUIに存在するかだけ検証して終了",
    )
    args = parser.parse_args()

    if args.check:
        ok = check_comfyui(args.comfy_url)
        return 0 if ok else 1

    base = Path(__file__).resolve().parent
    workflow_path = args.workflow or str(base / "ltx2_workflow_debug.json")
    if not os.path.isfile(workflow_path):
        print(f"ワークフローファイルが見つかりません: {workflow_path}")
        if "ltx2_i2v_from_ui" in workflow_path or "ltx2_i2v_ready" in workflow_path:
            print("ComfyUIでワークフローを開き、File -> Export (API) で保存してください。")
            print(
                "例: LTX-2_I2V_Distilled_wLora.json を読み込み、ltx2_workflows/ltx2_i2v_from_ui.json に保存"
            )
        return 1

    workflow = load_workflow(workflow_path)
    fix_workflow_paths(workflow)
    if args.prompt is not None:
        # ノード "5" が CLIP Text Encode (Prompt)
        if "5" in workflow and "inputs" in workflow["5"]:
            workflow["5"]["inputs"]["text"] = args.prompt
    if args.image is not None:
        if "1" in workflow and "inputs" in workflow["1"]:
            workflow["1"]["inputs"]["image"] = args.image

    # 送信前にノード検証
    result = validate_workflow_nodes(args.comfy_url, workflow)
    if result is None:
        print("ComfyUIに接続できません。起動してから再実行してください。")
        return 1
    ok, missing = result
    if not ok:
        print(f"ワークフローで使用されているノードのうち、ComfyUIに存在しません: {missing}")
        print(
            "  → .\\run_ltx2_diagnose.ps1 で互換ワークフローを検出するか、Export (API) で保存し直してください。"
        )
        return 1
    if args.dry_run:
        print("--dry-run: ノード検証OK。送信は行いません。")
        return 0

    print(f"ComfyUI: {args.comfy_url}")
    print("ワークフローを送信しています...")
    prompt_id = submit_workflow(args.comfy_url, workflow)
    if not prompt_id:
        return 1
    print(f"prompt_id: {prompt_id}")

    if args.no_wait:
        print("送信のみ完了。状態は ComfyUI のキュー/履歴で確認してください。")
        return 0

    print("完了を待機しています...")
    history = wait_for_completion(args.comfy_url, prompt_id, timeout=args.timeout)
    if not history:
        return 1

    paths = extract_output_paths(history, prompt_id)
    if paths:
        print("出力ファイル:")
        for subfolder, filename in paths:
            print(f"  {subfolder}/{filename}")
    else:
        print("履歴を取得しましたが、動画出力ノードの結果が見つかりません。")
        print("ComfyUIの出力フォルダを確認してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
