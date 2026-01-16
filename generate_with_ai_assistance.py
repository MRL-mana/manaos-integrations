#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI支援付き画像生成スクリプト
Brave Search APIとBase AI APIを活用してプロンプトを改善
"""

import requests
import time
import sys
import io
import random
from pathlib import Path
from dotenv import load_dotenv

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 環境変数を読み込む
load_dotenv(Path(__file__).parent / '.env')

# ManaOS Core APIをインポート
try:
    from manaos_core_api import ManaOSCoreAPI
    MANAOS_AVAILABLE = True
except ImportError:
    MANAOS_AVAILABLE = False
    print("[WARN] ManaOS Core APIが利用できません")

GALLERY_API = "http://localhost:5559/api/generate"
UNIFIED_API = "http://localhost:9500"

# まだ使っていないモデル
other_models = [
    "realisian_v60.safetensors",
    "realisticVisionV60B1_v51HyperVAE.safetensors",
    "speciosaRealistica_v12b.safetensors",
    "shibari_v20.safetensors",
    "qqq-BDSM-v3-000010.safetensors",
    "0482 dildo masturbation_v1_pony.safetensors",
    "0687 public indecency_v1_pony.safetensors"
]

def search_prompt_ideas(query: str) -> list:
    """Brave Search APIでプロンプトのアイデアを検索"""
    if not MANAOS_AVAILABLE:
        return []
    
    try:
        manaos = ManaOSCoreAPI()
        result = manaos.act("brave_search", {
            "query": query,
            "count": 5,
            "search_lang": "jp"
        })
        
        if result.get("status") == "success" and result.get("results"):
            ideas = []
            for item in result["results"][:3]:
                title = item.get("title", "")
                url = item.get("url", "")
                ideas.append({"title": title, "url": url})
            return ideas
    except Exception as e:
        print(f"[WARN] Brave Searchエラー: {e}")
    
    return []

def improve_prompt_with_ai(prompt: str) -> str:
    """Base AI APIでプロンプトを改善"""
    if not MANAOS_AVAILABLE:
        return prompt
    
    try:
        manaos = ManaOSCoreAPI()
        improvement_prompt = f"""以下の画像生成プロンプトを改善してください。
より詳細で、高品質な画像が生成されるようにプロンプトを最適化してください。
元のプロンプト: {prompt}

改善されたプロンプトのみを返してください。"""
        
        result = manaos.act("base_ai_chat", {
            "prompt": improvement_prompt,
            "use_free": True
        })
        
        if result.get("result") and result["result"].get("response"):
            improved = result["result"]["response"].strip()
            # プロンプトのみを抽出（余計な説明を削除）
            if improved.startswith("プロンプト:"):
                improved = improved.split("プロンプト:", 1)[1].strip()
            if improved.startswith("改善されたプロンプト:"):
                improved = improved.split("改善されたプロンプト:", 1)[1].strip()
            return improved
    except Exception as e:
        print(f"[WARN] Base AIエラー: {e}")
    
    return prompt

def generate_varied_prompt(use_ai_assistance: bool = True):
    """バリエーション豊かなプロンプトを生成（AI支援付き）"""
    # 基本要素
    poses = [
        "sitting", "lying down", "standing", "kneeling", "bent over", 
        "on all fours", "spread legs", "arms up", "back arch", "side view",
        "cowgirl position", "missionary position", "doggy style", "69 position"
    ]
    expressions = [
        "smile", "innocent look", "seductive expression", "pleasure face", 
        "blushing", "winking", "open mouth", "tongue out", "closed eyes", 
        "looking at viewer", "ecstatic expression", "moaning"
    ]
    styles = [
        "clear and pure gyaru style", "cute gyaru", "innocent gyaru", 
        "sexy gyaru", "kawaii gyaru", "pure gyaru", "clear gyaru style",
        "gyaru style", "gyaru fashion"
    ]
    scenes = [
        "sexual act", "intimate moment", "erotic scene", "passionate moment",
        "intimate scene", "erotic act", "passionate act", "intimate act",
        "making love", "having sex", "foreplay"
    ]
    qualities = [
        "high quality", "detailed", "masterpiece", "best quality", 
        "ultra detailed", "8k", "photorealistic", "cinematic lighting"
    ]
    
    # 基本プロンプトを生成
    style = random.choice(styles)
    pose = random.choice(poses)
    expression = random.choice(expressions)
    scene = random.choice(scenes)
    quality = random.choice(qualities)
    
    prompt_parts = [
        style,
        f"naked, {pose}",
        expression,
        scene,
        "beautiful body",
        quality
    ]
    
    base_prompt = ", ".join(prompt_parts)
    
    # AI支援でプロンプトを改善
    if use_ai_assistance:
        print("  [AI] プロンプトを改善中...")
        improved_prompt = improve_prompt_with_ai(base_prompt)
        if improved_prompt != base_prompt:
            print(f"  [AI] プロンプト改善完了")
            return improved_prompt
    
    return base_prompt

def search_trending_prompts():
    """最新のプロンプトトレンドを検索"""
    print("  [検索] 最新のプロンプトトレンドを検索中...")
    ideas = search_prompt_ideas("stable diffusion prompt ideas 2024")
    
    if ideas:
        print(f"  [検索] {len(ideas)}件のアイデアを取得")
        for i, idea in enumerate(ideas, 1):
            print(f"    {i}. {idea['title']}")
    
    return ideas

print("=" * 70)
print("AI支援付き画像生成スクリプト")
print("Brave Search APIとBase AI APIを活用してプロンプトを改善")
print("=" * 70)
print()

# ManaOS統合の確認
if MANAOS_AVAILABLE:
    print("[OK] ManaOS Core API統合: 利用可能")
    print("  - Brave Search API: プロンプトアイデア検索")
    print("  - Base AI API: プロンプト改善")
else:
    print("[WARN] ManaOS Core API統合: 利用不可（基本モードで実行）")
print()

# 最新トレンドを検索（オプション）
use_trending = input("最新のプロンプトトレンドを検索しますか？ (y/n): ").lower() == 'y'
if use_trending and MANAOS_AVAILABLE:
    trending_ideas = search_trending_prompts()
    print()

# AI支援の使用確認
use_ai = input("AI支援でプロンプトを改善しますか？ (y/n): ").lower() == 'y'
print()

job_ids = []

# サンプラーとスケジューラーのバリエーション
samplers = ["dpmpp_2m", "dpmpp_2s_ancestral", "euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral"]
schedulers = ["karras", "normal", "exponential", "sgm_uniform"]

for i, model in enumerate(other_models):
    print(f"[{i+1}/{len(other_models)}] モデル: {model}")
    
    # プロンプト生成（AI支援付き）
    prompt = generate_varied_prompt(use_ai_assistance=use_ai)
    print(f"  プロンプト: {prompt[:100]}...")
    
    # 毎回異なるパラメータを設定
    seed = random.randint(1, 2**32 - 1)
    steps = random.choice([30, 35, 40, 45])
    guidance_scale = round(random.uniform(7.0, 8.5), 1)
    sampler = random.choice(samplers)
    scheduler = random.choice(schedulers)
    
    # 解像度も変える
    aspect_ratios = [
        (768, 1024),  # 縦長
        (1024, 768),  # 横長
        (832, 1216),  # より縦長
        (1216, 832),  # より横長
        (896, 1152),  # 中程度の縦長
    ]
    width, height = random.choice(aspect_ratios)
    
    print(f"  解像度: {width}x{height}")
    print(f"  ステップ: {steps}, CFG: {guidance_scale}, サンプラー: {sampler}, スケジューラー: {scheduler}, seed: {seed}")
    
    payload = {
        "prompt": prompt,
        "model": model,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "width": width,
        "height": height,
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": seed,
        "mufufu_mode": True
    }
    
    try:
        response = requests.post(
            GALLERY_API,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                job_ids.append((job_id, model))
                print(f"  [OK] ジョブID: {job_id}")
            else:
                print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        else:
            print(f"  [HTTP ERROR] {response.status_code}")
            print(f"    レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
    
    # リクエスト間隔を空ける
    if i < len(other_models) - 1:
        time.sleep(2)
    print()

print("=" * 70)
print(f"[完了] {len(job_ids)}件の画像生成ジョブを送信しました")
print("=" * 70)
print()
print("ジョブID一覧:")
for i, (job_id, model) in enumerate(job_ids, 1):
    print(f"  {i}. {job_id} ({model})")
print()
print("画像生成の進行状況は以下で確認できます:")
print("  http://localhost:5559/api/job/<job_id>")
print()
print("生成された画像は以下で確認できます:")
print("  http://localhost:5559/api/images")

