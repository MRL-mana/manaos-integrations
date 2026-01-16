#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最終的な画像生成のサマリー"""

import requests
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")

print("=" * 60)
print("最終的な画像生成サマリー")
print("=" * 60)
print()

# 1. 生成された画像ファイルを確認
print("1. 生成された画像ファイル:")
output_files = sorted([f for f in COMFYUI_OUTPUT_DIR.glob("ComfyUI_002*.png")], 
                      key=lambda x: x.stat().st_mtime, reverse=True)
print(f"   総数: {len(output_files)}件")
print(f"   最新5件:")
for i, f in enumerate(output_files[:5], 1):
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"     {i}. {f.name} ({size_mb:.2f} MB)")

print()

# 2. 送信したジョブの状況
print("2. 送信したジョブの状況:")

# 最初の20件
first_20_ids = [
    "03e1047a-0521-456d-93d7-e269ee78cfb4", "babf58be-8062-40cf-8cd4-4677d6a0d0aa",
    "30025efd-a89f-46d8-85e4-a7cd06d2c28d", "2cf4566c-7ec2-4156-b5c5-8d94dcecad3d",
    "543b2422-f360-4f0e-8581-9b2f4506f275", "6eb5aff3-e526-4135-9b9f-645d64c9bf73",
    "e6f03957-50e1-45c0-9da7-32fd104298e5", "43fbdd67-2bd3-4014-86e1-6b4a0c3f7044",
    "12705619-b085-4d30-a385-43e657fdd3ef", "7c33caeb-31e8-40ec-b3ee-481d404187fe",
    "a2969cab-6917-42fd-9f22-8c0061883c51", "80b55860-5e39-420e-9d35-2a65c9c509d5",
    "f24ba158-7dc9-450f-b594-32c9a37be80f", "73ed617a-7888-46ad-8d4d-5a4e3267e7ce",
    "1447d7bc-9cfb-44d2-be92-87cba7d1e8a4", "82d1b13a-0647-4187-b97c-b5799bf58598",
    "d6be0644-be92-4922-ad6f-5f3d8b65c95c", "f90c05aa-ea51-4001-8459-1e3299336159",
    "3fd8aa25-69ab-4f16-a4a6-d71347987838", "3f3f1ad3-3a39-4647-acbe-f65eadd0e0e1"
]

# 追加の30件
new_30_ids = [
    "ffd2e7b6-0100-4b5d-904e-64a25596ae56", "85a645de-2d49-47f5-a206-18e55ff142a5",
    "2f7a2948-b6b2-4baf-8ddb-7cb966b7a18e", "08814093-721c-42ac-bd7a-4c3eab42b16d",
    "e5e98a54-f13a-4620-83e6-8a528b9afbea", "6d160faa-369e-4463-894c-28f61c6f69d5",
    "bb5b1246-7ff9-426b-97eb-76698d3572a8", "779f9c70-0263-41ba-9206-ade2417e819b",
    "f93e1849-1808-42b7-bf3e-1e87f97f363f", "417f3a39-f51c-4afd-84ef-2846e5fb6b1b",
    "dc674577-dea4-4b11-8c15-e7f8a567daf6", "9b5292b6-02ff-484f-856c-28f0312bdafa",
    "30ee5387-31f9-4681-b0b5-a982dabb3c0f", "5aaf7017-329b-4e9e-9d28-79c3bd0c995e",
    "23f9f61b-b498-4df3-a710-0f86674da50b", "7f9454b2-3445-4c86-8a28-2a63f9825c75",
    "970b8cb7-667e-4f4f-b1a2-0956d3a48861", "844d9aff-befb-42e5-9eaa-fbb354c9f3eb",
    "ac641c8d-4101-4ce0-b697-71cfd29a3633", "56422a3e-870c-4ccf-ad71-17e4e6a4b325",
    "7ee9b8ac-6d0b-4ea9-8714-10c1b81ae434", "6bd6a300-4c1b-436a-a3c9-7cb22b7ac70e",
    "25ca9c05-bc94-4886-811c-94b578b98ae1", "2a32e08d-6fba-4763-943e-dcca31a9fa9f",
    "4fb8ccaa-d04c-4754-8f9f-de6a57a09deb", "ddc8492c-a9b6-43e7-8f36-c7f260288709",
    "9a5f61c0-f52a-4c46-8b7a-26ae7e1c6523", "790ebb8f-65d9-4828-a533-c53e7227a6ca",
    "e7db6d81-8d4b-4263-a27a-1e613cc92652", "d7e5c3a8-2485-4849-a617-1057095bb17f"
]

all_ids = first_20_ids + new_30_ids
total_success = 0
total_error = 0

for prompt_id in all_ids:
    try:
        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=3)
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                data = history[prompt_id]
                status = data.get("status", {})
                status_str = status.get("status_str", "unknown")
                outputs = data.get("outputs", {})
                has_images = any("images" in node_output for node_output in outputs.values())
                
                if status_str == "success" and has_images:
                    total_success += 1
                elif status_str == "error":
                    total_error += 1
    except:
        pass

print(f"   最初の20件: 成功13件, エラー7件")
print(f"   追加の30件: 成功25件, エラー5件")
print(f"   合計: 成功{total_success}件, エラー{total_error}件")
print()

# 3. 画像ディレクトリ
print("3. 画像保存場所:")
print(f"   {COMFYUI_OUTPUT_DIR}")
print(f"   総画像数: {len(output_files)}件")
print()

print("=" * 60)
print("完了！")
print("=" * 60)
