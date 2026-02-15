#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""失敗の原因を分析"""

import requests
import sys
import io

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

COMFYUI_URL = "http://127.0.0.1:8188"

print("=" * 60)
print("失敗の原因分析")
print("=" * 60)
print()

# エラーが発生したプロンプトID
error_prompt_ids = [
    "19aa2f76-8827-4cf0-8cac-a738d18cf76d",  # realisticVisionV60B1_v51HyperVAE
    "7188621d-c192-4ebd-99d4-abefee614b52",  # realisticVisionV60B1_v51HyperVAE
    "8468346c-0819-4bfb-897f-605e37511f5b",  # realisticVisionV60B1_v51HyperVAE
    "3e94fa44-d357-4cc6-86cb-cb379f04c4f5",  # realisticVisionV60B1_v51HyperVAE
    "3b013a13-c4dd-431a-bdf9-d7ecf596244e",  # realisticVisionV60B1_v51HyperVAE
]

print("エラーが発生したジョブの詳細:")
print()

for i, prompt_id in enumerate(error_prompt_ids, 1):
    try:
        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                data = history[prompt_id]
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                
                if status_str == "error":
                    messages = status.get("messages", [])
                    for msg in messages:
                        if msg[0] == "execution_error":
                            error_data = msg[1]
                            error_msg = error_data.get('exception_message', 'N/A')
                            node_type = error_data.get('node_type', 'N/A')
                            
                            print(f"[{i}] {prompt_id[:30]}...")
                            print(f"  エラータイプ: {node_type}")
                            print(f"  エラーメッセージ: {error_msg}")
                            
                            # ワークフローからモデル名を取得
                            prompt_data = data.get("prompt", {})
                            if prompt_data:
                                for node_id, node_data in prompt_data.items():
                                    if node_data.get("class_type") == "CheckpointLoaderSimple":
                                        model_name = node_data.get("inputs", {}).get("ckpt_name", "N/A")
                                        print(f"  使用モデル: {model_name}")
                            print()
    except Exception as e:
        print(f"[{i}] {prompt_id[:30]}... [確認エラー] - {e}")
        print()

print("=" * 60)
print("分析結果:")
print("=" * 60)
print()
print("失敗の原因:")
print("  1. realisticVisionV60B1_v51HyperVAE.safetensors モデルファイルの問題")
print("     - エラー: 'Error while deserializing header: incomplete metadata'")
print("     - 原因: モデルファイルのメタデータが不完全または破損している可能性")
print()
print("  2. 解決方法:")
print("     - realisian_v60.safetensors を使用（このモデルは正常に動作）")
print("     - または、realisticVisionV60B1_v51HyperVAE.safetensors を再ダウンロード")
print()
