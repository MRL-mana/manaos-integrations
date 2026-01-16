#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像生成スクリプト（即座に実行）"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_image_interactive(prompt: str = None):
    """画像生成（プロンプト指定可能）"""
    
    print("=" * 60)
    print("🎨 画像生成を開始します！")
    print("=" * 60)
    
    # プロンプトを取得（引数またはデフォルト値）
    if not prompt:
        # デフォルトプロンプト
        user_prompt = """
        masterpiece, best quality, ultra detailed, 8k,
        beautiful landscape, mountains, sunset, cinematic lighting,
        highly detailed, depth of field, soft colors
        """
        print(f"デフォルトプロンプトを使用: {user_prompt[:50]}...")
    else:
        user_prompt = prompt
        print(f"プロンプト: {user_prompt[:100]}...")
    
    # ネガティブプロンプト
    negative_prompt = "blurry, low quality, distorted, ugly, worst quality, watermark, text"
    
    # 画像生成を試行（複数の方法を順番に試す）
    result = None
    
    # 方法1: 画像生成統合を使用
    try:
        from image_generation_integration import ImageGenerationIntegration
        logger.info("✓ 画像生成統合を初期化中...")
        integration = ImageGenerationIntegration()
        
        logger.info("🎨 画像生成中...")
        result = integration.generate_and_stock(
            prompt=user_prompt.strip(),
            negative_prompt=negative_prompt,
            width=768,
            height=768,
            num_inference_steps=30,
            guidance_scale=7.5,
            use_hf=True
        )
        
        if result.get("success"):
            logger.info("✅ 画像生成成功！")
            image_path = result.get("image_path")
            if image_path:
                logger.info(f"📷 画像パス: {image_path}")
                return result
    except ImportError as e:
        logger.warning(f"画像生成統合が利用できません: {e}")
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
    
    # 方法2: HuggingFace統合を直接使用
    if not result or not result.get("success"):
        try:
            from huggingface_integration import HuggingFaceManaOSIntegration
            logger.info("✓ HuggingFace統合を初期化中...")
            hf_integration = HuggingFaceManaOSIntegration()
            
            logger.info("🎨 HuggingFaceで画像生成中...")
            result = hf_integration.generate_image(
                prompt=user_prompt.strip(),
                negative_prompt=negative_prompt,
                width=768,
                height=768,
                num_inference_steps=30,
                guidance_scale=7.5,
                auto_stock=True
            )
            
            if result.get("success"):
                logger.info("✅ 画像生成成功！")
                images = result.get("images", [])
                if images:
                    logger.info(f"📷 生成された画像: {len(images)}枚")
                    for i, img in enumerate(images, 1):
                        logger.info(f"  {i}. {img.get('path')}")
                    return result
        except ImportError as e:
            logger.warning(f"HuggingFace統合が利用できません: {e}")
        except Exception as e:
            logger.error(f"HuggingFace画像生成エラー: {e}")
    
    # 方法3: Gallery APIサーバーを使用（ポート5559）
    if not result or not result.get("success"):
        try:
            import requests
            import os
            gallery_api = os.getenv("GALLERY_API_URL", "http://localhost:5559")
            
            logger.info(f"✓ Gallery APIサーバーに接続中: {gallery_api}")
            
            # 利用可能なモデルを取得（デフォルトモデルを使用）
            # Gallery APIサーバーはモデルを自動検出するので、指定しなくてもOK
            model = None  # モデルを指定しない場合は、サーバーが自動選択
            
            payload = {
                "prompt": user_prompt.strip(),
                "negative_prompt": negative_prompt,
                "width": 768,
                "height": 768,
                "steps": 30,
                "guidance_scale": 7.5,
                "sampler": "dpmpp_2m",
                "scheduler": "karras"
            }
            
            if model:
                payload["model"] = model
            
            # Gallery APIで画像生成
            response = requests.post(
                f"{gallery_api}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    job_id = data.get("job_id")
                    logger.info(f"✅ 画像生成を開始しました（ジョブID: {job_id}）")
                    logger.info(f"   ステータス確認: {gallery_api}/api/job/{job_id}")
                    logger.info(f"   画像一覧: {gallery_api}/api/images")
                    return {"success": True, "job_id": job_id, "method": "gallery_api", "gallery_url": gallery_api}
                else:
                    error_msg = data.get('error', '不明なエラー')
                    logger.error(f"Gallery APIエラー: {error_msg}")
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
                logger.error(f"Gallery API HTTPエラー: {error_msg}")
        except ImportError:
            logger.warning("requestsライブラリが利用できません")
        except Exception as e:
            logger.error(f"Gallery APIエラー: {e}")
    
    # 方法4: ComfyUI統合を直接使用
    if not result or not result.get("success"):
        try:
            from comfyui_integration import ComfyUIIntegration
            logger.info("✓ ComfyUI統合を初期化中...")
            comfyui = ComfyUIIntegration()
            
            if comfyui.is_available():
                logger.info("🎨 ComfyUIで画像生成中...")
                prompt_id = comfyui.generate_image(
                    prompt=user_prompt.strip(),
                    negative_prompt=negative_prompt,
                    width=768,
                    height=768
                )
                
                if prompt_id:
                    logger.info(f"✅ 画像生成を開始しました（プロンプトID: {prompt_id}）")
                    logger.info("   ComfyUIのUIで生成状況を確認してください")
                    logger.info(f"   http://localhost:8188 で確認できます")
                    return {"success": True, "prompt_id": prompt_id, "method": "comfyui_direct"}
                else:
                    logger.error("ComfyUI画像生成に失敗しました")
            else:
                logger.warning("ComfyUIが利用できません")
        except ImportError as e:
            logger.warning(f"ComfyUI統合が利用できません: {e}")
        except Exception as e:
            logger.error(f"ComfyUI統合エラー: {e}")
    
    # 方法5: 統一APIサーバーを使用
    if not result or not result.get("success"):
        try:
            import requests
            import os
            api_url = os.getenv("UNIFIED_API_URL", "http://localhost:5000")
            
            logger.info(f"✓ 統一APIサーバーに接続中: {api_url}")
            payload = {
                "prompt": user_prompt.strip(),
                "negative_prompt": negative_prompt,
                "width": 768,
                "height": 768,
                "steps": 30,
                "cfg_scale": 7.5
            }
            
            # ComfyUIエンドポイントを試す
            response = requests.post(
                f"{api_url}/api/comfyui/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id")
                logger.info(f"✅ 画像生成を開始しました（プロンプトID: {prompt_id}）")
                logger.info("   ComfyUIのUIで生成状況を確認してください")
                return {"success": True, "prompt_id": prompt_id, "method": "comfyui"}
        except ImportError:
            logger.warning("requestsライブラリが利用できません")
        except Exception as e:
            logger.error(f"統一APIサーバーエラー: {e}")
    
    # すべて失敗した場合
    if not result or not result.get("success"):
        logger.error("❌ すべての画像生成方法が利用できませんでした")
        logger.info("💡 以下のいずれかを確認してください:")
        logger.info("   1. HuggingFace統合が正しく設定されているか")
        logger.info("   2. ComfyUIサーバーが起動しているか（ポート8188）")
        logger.info("   3. 統一APIサーバーが起動しているか（ポート5000）")
        return {"success": False, "error": "画像生成機能が利用できません"}
    
    return result

if __name__ == "__main__":
    import os
    
    try:
        # コマンドライン引数からプロンプトを取得
        import sys
        prompt = None
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
        
        result = generate_image_interactive(prompt=prompt)
        
        print("\n" + "=" * 60)
        if result.get("success"):
            print("✅ 画像生成が完了しました！")
            if result.get("image_path"):
                print(f"📷 画像: {result['image_path']}")
            elif result.get("prompt_id"):
                print(f"🆔 プロンプトID: {result['prompt_id']}")
        else:
            print(f"❌ エラー: {result.get('error', '不明なエラー')}")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによって中断されました")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
