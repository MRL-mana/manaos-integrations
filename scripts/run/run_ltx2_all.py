#!/usr/bin/env python3
"""
LTX-2 動画生成を一括実行する。
1) ltx2_i2v_from_ui.json があればパッチ → 送信
2) なければ例ワークフローを変換 → パッチ → 送信を試行（ノード不足で失敗する場合あり）
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / "ltx2_workflows"
FROM_UI = WORKFLOWS / "ltx2_i2v_from_ui.json"
READY = WORKFLOWS / "ltx2_i2v_ready.json"
EXAMPLE = Path(
    r"C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\LTX-2_I2V_Distilled_wLora.json"
)


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    r = subprocess.run(cmd, cwd=cwd or ROOT, shell=False)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LTX-2 動画生成を一括実行")
    parser.add_argument("--prompt", default="a calm sea, sunset", help="プロンプト")
    parser.add_argument("--no-wait", action="store_true", help="送信のみで待機しない")
    parser.add_argument(
        "--comfy-url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    )
    parser.add_argument(
        "--from-ui-path",
        type=str,
        default=None,
        help="Export (API) で保存した JSON のパス（保存先を選べない場合に指定）",
    )
    args = parser.parse_args()

    WORKFLOWS.mkdir(parents=True, exist_ok=True)

    # 指定があればそのファイルを ltx2_workflows にコピーして使う
    from_ui_path = Path(args.from_ui_path).resolve() if args.from_ui_path else None
    if from_ui_path and from_ui_path.exists():
        import shutil

        shutil.copy2(from_ui_path, FROM_UI)
        print(f"Copied: {from_ui_path} -> {FROM_UI}")

    # 1) UI から Export した JSON があればそれを使う
    if FROM_UI.exists():
        print("[1/2] ltx2_i2v_from_ui.json をパッチしています...")
        if not run(
            [sys.executable, str(ROOT / "ltx2_patch_workflow.py"), str(FROM_UI), str(READY)]
        ):
            return 1
        print("[2/2] ComfyUI に送信しています...")
        cmd = [
            sys.executable,
            str(ROOT / "run_ltx2_generate.py"),
            "--workflow",
            str(READY),
            "--prompt",
            args.prompt,
            "--comfy-url",
            args.comfy_url,
        ]
        if args.no_wait:
            cmd.append("--no-wait")
        ok = run(cmd)
        if ok:
            print("Done.")
        return 0 if ok else 1

    # 2) なければ例ワークフローを変換 → パッチ → 送信を試行
    if not EXAMPLE.exists():
        print("ltx2_i2v_from_ui.json がありません。")
        print("ComfyUI でワークフローを開き、File -> Export (API) で保存してください:")
        print(f"  保存先: {FROM_UI}")
        print("手順: LTX2_LOAD_WORKFLOW.md を参照")
        return 1

    print("[1/3] 例ワークフローを API 形式に変換しています...")
    expanded = WORKFLOWS / "ltx2_i2v_expanded.json"
    if not run(
        [sys.executable, str(ROOT / "ltx2_workflow_to_api.py"), str(EXAMPLE), str(expanded)]
    ):
        return 1
    print("[2/3] パッチしています...")
    if not run([sys.executable, str(ROOT / "ltx2_patch_workflow.py"), str(expanded), str(READY)]):
        return 1
    print("[3/3] ComfyUI に送信しています...")
    cmd = [
        sys.executable,
        str(ROOT / "run_ltx2_generate.py"),
        "--workflow",
        str(READY),
        "--prompt",
        args.prompt,
        "--comfy-url",
        args.comfy_url,
    ]
    if args.no_wait:
        cmd.append("--no-wait")
    if run(cmd):
        return 0
    print("")
    print("送信に失敗しました。利用中の ComfyUI に合わせるため、次を実行してください:")
    print("  1. 一括診断で互換ワークフローを確認: .\\run_ltx2_diagnose.ps1")
    print("  2. 互換ワークフローがあれば ComfyUI で開き File -> Export (API) で保存:")
    print(f"     {FROM_UI}")
    print("  3. または LTX-2_I2V_Distilled_wLora.json をドラッグで開き Export (API) で保存")
    print('  4. 再度実行: python run_ltx2_all.py --prompt "your prompt"')
    return 1


if __name__ == "__main__":
    sys.exit(main())
