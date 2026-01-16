"""
マナごのみのムフフ画像生成スクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# Windowsコンソールの文字コード問題を回避（ログ出力のみ）
import os
if sys.platform == "win32":
    # 環境変数でUTF-8を強制
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from manaos_core_api import ManaOSCoreAPI

# ムフフモード設定のインポート（身体崩れ対策強化版）
try:
    from mufufu_config import (
        MUFUFU_NEGATIVE_PROMPT,
        ANATOMY_POSITIVE_TAGS,
        OPTIMIZED_PARAMS
    )
except ImportError:
    # フォールバック: 旧バージョン
    MUFUFU_NEGATIVE_PROMPT = ""
    ANATOMY_POSITIVE_TAGS = ""
    OPTIMIZED_PARAMS = {}

def generate_mana_mufufu_image():
    """マナごのみのムフフ画像を生成"""
    print("[画像生成] マナごのみのムフフ画像生成を開始...")
    
    api = ManaOSCoreAPI()
    
    # プロンプト（「ムフフ」という悪戯っぽい笑顔のマナごのみ）
    # まずSDプロンプト生成機能で最適化されたプロンプトを生成
    print("[プロンプト生成] SDプロンプトを生成中...")
    sd_prompt_result = api.act("generate_sd_prompt", {
        "prompt": "マナごのみのムフフ画像生成、悪戯っぽい笑顔、目を細めて笑っている、手を口の前に当てて笑っている、小悪魔的な雰囲気、可愛いアニメキャラクター"
    })
    
    if sd_prompt_result.get("success"):
        base_prompt = sd_prompt_result.get("prompt", "")
        print(f"[生成されたプロンプト] {base_prompt[:100]}...")
    else:
        # フォールバック: より具体的なプロンプト
        base_prompt = "managonomi, cute anime girl, mischievous grin, eyes closed with smile, hand covering mouth while laughing, playful expression, winking, evil smile, kawaii anime character, fluffy hair, pastel colors, soft lighting, anime illustration, high quality, detailed, mufufu expression"
        print("[フォールバック] デフォルトプロンプトを使用")
    
    # 身体崩れ対策: ポジティブプロンプトに身体崩れ対策タグを追加
    if ANATOMY_POSITIVE_TAGS:
        prompt = f"{ANATOMY_POSITIVE_TAGS}, {base_prompt}"
        print("[身体崩れ対策] ポジティブプロンプトに身体崩れ対策タグを追加")
    else:
        prompt = base_prompt
    
    # ネガティブプロンプト（身体崩れ対策強化版）
    if MUFUFU_NEGATIVE_PROMPT:
        negative_prompt = MUFUFU_NEGATIVE_PROMPT
        print("[身体崩れ対策] 強化版ネガティブプロンプトを使用")
    else:
        # フォールバック: 旧バージョン
        negative_prompt = "nsfw, adult content, explicit, low quality, blurry, distorted, bad anatomy, bad proportions, serious expression, sad, angry, crying, realistic photo, 3d render"
    
    print(f"[プロンプト] {prompt[:80]}...")
    print("[生成中] 画像生成中...")
    
    # 身体崩れ対策: パラメータを最適化
    if OPTIMIZED_PARAMS:
        width = max(OPTIMIZED_PARAMS.get("min_width", 1024), 1024)
        height = max(OPTIMIZED_PARAMS.get("min_height", 1024), 1024)
        num_inference_steps = OPTIMIZED_PARAMS.get("steps", 50)
        guidance_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
        print(f"[身体崩れ対策] パラメータを最適化: {width}x{height}, steps={num_inference_steps}, guidance={guidance_scale}")
    else:
        # フォールバック: 旧バージョン（ただし解像度は最低1024x1024を推奨）
        width = 1024
        height = 1024
        num_inference_steps = 50
        guidance_scale = 7.5
        print(f"[警告] 解像度が低いと身体崩れが増える可能性があります: {width}x{height}")
    
    # 画像生成を実行
    result = api.act("generate_image", {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "model_id": "runwayml/stable-diffusion-v1-5",
        "width": width,
        "height": height,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "auto_stock": True
    })
    
    if result.get("success"):
        images = result.get("images", [])
        if images:
            image_path = images[0].get("path", "")
            print(f"[成功] 画像生成成功！")
            print(f"[保存先] {image_path}")
            
            # ストック情報がある場合
            if images[0].get("stock_info"):
                stock_info = images[0]["stock_info"]
                print(f"[ストックID] {stock_info.get('stock_id', 'N/A')}")
            
            return {
                "success": True,
                "image_path": image_path,
                "images": images
            }
        else:
            print("[警告] 画像が生成されませんでした")
            return {"success": False, "error": "画像が生成されませんでした"}
    else:
        error = result.get("error", "不明なエラー")
        print(f"[エラー] 画像生成失敗: {error}")
        return {"success": False, "error": error}

if __name__ == "__main__":
    try:
        result = generate_mana_mufufu_image()
        if result.get("success"):
            print("\n[完了] 画像生成が完了しました！")
            sys.exit(0)
        else:
            print(f"\n[エラー] {result.get('error')}")
            sys.exit(1)
    except Exception as e:
        print(f"\n[エラー] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
