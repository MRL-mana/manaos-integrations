"""
ComfyUI の Gemma Text Encoder 用 config.json を修正するスクリプト

Transformers が「Unrecognized model」を出す場合、
text_encoders/(gemmaフォルダ) 内の config.json に model_type がないことが原因です。
このスクリプトで model_type を追加または作成します。

使い方:
  set COMFYUI_PATH=C:\\ComfyUI  (Windows)
  python fix_gemma_config.py
"""

import json
import os
import sys
from pathlib import Path

# ComfyUI パス（環境変数またはデフォルト）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
TEXT_ENCODERS = COMFYUI_PATH / "models" / "text_encoders"

# Gemma3 テキストモデル用の最小 config（トークナイザー読み込みに必要）
GEMMA3_TEXT_CONFIG = {
    "model_type": "gemma3_text",
    "architectures": ["Gemma3ForCausalLM"],
    "vocab_size": 262144,
    "hidden_size": 3072,
    "num_hidden_layers": 38,
    "num_attention_heads": 16,
    "head_dim": 256,
    "intermediate_size": 8192,
    "max_position_embeddings": 32768,
    "rms_norm_eps": 1e-6,
    "rope_theta": 1000000.0,
    "bos_token_id": 2,
    "eos_token_id": 1,
    "pad_token_id": 0,
    "torch_dtype": "bfloat16",
}


def fix_config_json(config_path: Path) -> bool:
    """config.json に model_type を追加またはファイルを作成する。"""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"   [WARN] 読み込み失敗: {config_path} - {e}")
            return False
        if data.get("model_type"):
            print(f"   [OK] 既に model_type あり: {data['model_type']}")
            return True
        data["model_type"] = "gemma3_text"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   [FIX] model_type を追加: {config_path}")
            return True
        except OSError as e:
            print(f"   [ERR] 書き込み失敗: {config_path} - {e}")
            return False
    else:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(GEMMA3_TEXT_CONFIG, f, indent=2, ensure_ascii=False)
            print(f"   [NEW] config.json を作成: {config_path}")
            return True
        except OSError as e:
            print(f"   [ERR] 作成失敗: {config_path} - {e}")
            return False


def main():
    print("=" * 60)
    print("Gemma Text Encoder config.json 修正")
    print("=" * 60)
    print(f"ComfyUI: {COMFYUI_PATH}")
    print(f"text_encoders: {TEXT_ENCODERS}")
    if not TEXT_ENCODERS.exists():
        print("\n[ERR] text_encoders フォルダがありません。")
        print("  COMFYUI_PATH を確認するか、Gemma モデルを先に配置してください。")
        sys.exit(1)
    gemma_dirs = list(TEXT_ENCODERS.glob("*gemma*"))
    if not gemma_dirs:
        print("\n[WARN] *gemma* のフォルダがありません。")
        print("  例: models/text_encoders/gemma-3-12b-it-qat-q4_0-unquantized/")
        sys.exit(0)
    ok = 0
    for d in gemma_dirs:
        if not d.is_dir():
            continue
        print(f"\n対象: {d.name}")
        config_path = d / "config.json"
        if fix_config_json(config_path):
            ok += 1
    print("\n" + "=" * 60)
    if ok:
        print("完了。ComfyUI を再起動してからワークフローを再実行してください。")
    else:
        print("修正できたフォルダがありません。パスと権限を確認してください。")
    print("=" * 60)


if __name__ == "__main__":
    main()
