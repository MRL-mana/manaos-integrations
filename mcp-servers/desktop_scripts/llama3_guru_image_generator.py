"""
Llama 3 Guru Uncensored + Stable Diffusion 統合画像生成システム
Llama 3でプロンプトを生成し、Stable Diffusionで画像を生成
"""

import asyncio
import os
import sys
from typing import Optional, List
from datetime import datetime

# ローカルLLMヘルパーをインポート
try:
    from local_llm_helper_simple import LocalLLM
except ImportError:
    print("エラー: local_llm_helper_simple.py が見つかりません")
    sys.exit(1)

# Stable Diffusion生成器をインポート（オプショナル）
SD_AVAILABLE = False
StableDiffusionGenerator = None

def _try_import_sd():
    """Stable Diffusionを動的にインポート"""
    global SD_AVAILABLE, StableDiffusionGenerator
    if SD_AVAILABLE:
        return True
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.cursor'))
        from stable_diffusion_generator import StableDiffusionGenerator as SDGen
        StableDiffusionGenerator = SDGen
        SD_AVAILABLE = True
        return True
    except Exception as e:
        SD_AVAILABLE = False
        StableDiffusionGenerator = None
        return False


class Llama3GuruImageGenerator:
    """Llama 3 Guru Uncensored + Stable Diffusion統合画像生成クラス"""
    
    def __init__(
        self,
        llama_model: str = "gurubot/llama3-guru-uncensored:latest",
        sd_model_id: str = "runwayml/stable-diffusion-v1-5",
        ollama_url: str = "http://127.0.0.1:11434"
    ):
        """
        初期化
        
        Args:
            llama_model: Llama 3 Guru Uncensoredのモデル名
            sd_model_id: Stable DiffusionのモデルID
            ollama_url: OllamaのURL
        """
        self.llm = LocalLLM(url=ollama_url, default_model=llama_model)
        self.sd_generator = None
        self.sd_model_id = sd_model_id
        self.llama_model = llama_model
        
    async def check_llama_connection(self) -> bool:
        """Llama 3への接続を確認"""
        try:
            connected = await self.llm.check_connection()
            if connected:
                # モデル名を自動検出して更新
                found_model = await self.find_llama_model()
                if found_model and found_model != self.llama_model:
                    print(f"📌 モデルを自動検出: {found_model}")
                    self.llama_model = found_model
                    self.llm.default_model = found_model
            return connected
        except Exception as e:
            print(f"接続確認エラー: {e}")
            return False
    
    async def list_available_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        try:
            return await self.llm.list_models()
        except Exception as e:
            print(f"モデル一覧取得エラー: {e}")
            return []
    
    async def find_llama_model(self) -> Optional[str]:
        """Llama 3 Guru Uncensoredモデルを自動検出"""
        models = await self.list_available_models()
        
        # 優先順位で検索
        search_patterns = [
            "gurubot/llama3-guru-uncensored",
            "llama3-guru-uncensored",
            "llama3:guru-uncensored",
            "llama3-guru",
            "guru-uncensored",
            "llama3"
        ]
        
        for pattern in search_patterns:
            for model in models:
                if pattern.lower() in model.lower():
                    return model
        
        # 見つからない場合は最初のllamaモデルを返す
        for model in models:
            if "llama" in model.lower():
                return model
        
        return None
    
    async def generate_prompt(
        self,
        user_request: str,
        style: str = "detailed",
        language: str = "english"
    ) -> dict:
        """
        Llama 3 Guru Uncensoredで画像生成プロンプトを生成
        
        Args:
            user_request: ユーザーのリクエスト（例: "美しい風景"）
            style: スタイル（detailed, artistic, realistic, anime, etc.）
            language: プロンプトの言語（english推奨）
        
        Returns:
            {"prompt": str, "negative_prompt": str} の辞書
        """
        system_prompt = """あなたは画像生成のためのプロンプト作成の専門家です。
ユーザーのリクエストに基づいて、Stable Diffusionで使用する高品質なプロンプトを生成してください。

プロンプトの要件:
- 英語で記述する
- 具体的で詳細な描写を含める
- 画質向上のキーワードを含める（highly detailed, 4k, professional photography等）
- スタイルや雰囲気を明確に指定する
- カンマ区切りで複数の要素を並べる

ネガティブプロンプトには以下を含める:
- blurry, low quality, distorted, ugly, bad anatomy, bad proportions
- その他、避けたい要素があれば追加

出力形式:
プロンプト: [生成されたプロンプト]
ネガティブプロンプト: [生成されたネガティブプロンプト]
"""
        
        user_prompt = f"""ユーザーリクエスト: {user_request}
スタイル: {style}
言語: {language}

上記のリクエストに基づいて、Stable Diffusion用のプロンプトとネガティブプロンプトを生成してください。"""
        
        print(f"\n{'='*60}")
        print(f"Llama 3 Guru Uncensoredでプロンプト生成中...")
        print(f"リクエスト: {user_request}")
        print(f"{'='*60}\n")
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.llm.chat(messages, model=self.llama_model)
            
            # レスポンスからプロンプトとネガティブプロンプトを抽出
            prompt = ""
            negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
            
            # レスポンスを解析
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('プロンプト:') or line.startswith('Prompt:'):
                    prompt = line.split(':', 1)[1].strip()
                elif line.startswith('ネガティブプロンプト:') or line.startswith('Negative Prompt:'):
                    negative_prompt = line.split(':', 1)[1].strip()
            
            # プロンプトが見つからない場合、レスポンス全体を使用
            if not prompt:
                # レスポンスから最初の長い文をプロンプトとして使用
                prompt = response.strip()
                # 最初の2-3文をプロンプトとして使用
                sentences = prompt.split('.')
                if len(sentences) > 2:
                    prompt = '. '.join(sentences[:2]) + '.'
            
            # デフォルトのネガティブプロンプトを追加
            if not negative_prompt or negative_prompt == "":
                negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
            
            print(f"生成されたプロンプト:")
            print(f"  {prompt}")
            print(f"\nネガティブプロンプト:")
            print(f"  {negative_prompt}")
            
            return {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "raw_response": response
            }
            
        except Exception as e:
            print(f"プロンプト生成エラー: {e}")
            # フォールバック: ユーザーリクエストをそのまま使用
            prompt = f"{user_request}, highly detailed, 4k, professional photography"
            negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
            return {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "raw_response": ""
            }
    
    def initialize_sd(self, disable_safety_checker: bool = False):
        """Stable Diffusion生成器を初期化"""
        if not _try_import_sd():
            raise ImportError("Stable Diffusionは利用できません。diffusersパッケージをインストールしてください。")
        if self.sd_generator is None:
            print(f"\n{'='*60}")
            print(f"Stable Diffusion生成器を初期化中...")
            print(f"モデル: {self.sd_model_id}")
            if disable_safety_checker:
                print("安全フィルター: 無効化（ローカル環境用）")
            print(f"{'='*60}\n")
            self.sd_generator = StableDiffusionGenerator(  # type: ignore[operator]
                model_id=self.sd_model_id,
                disable_safety_checker=disable_safety_checker
            )
    
    async def generate_image(
        self,
        user_request: str,
        style: str = "detailed",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        output_dir: str = "generated_images",
        use_llama_prompt: bool = True
    ):
        """
        画像を生成
        
        Args:
            user_request: ユーザーのリクエスト
            style: スタイル
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数
            guidance_scale: ガイダンススケール
            output_dir: 出力ディレクトリ
            use_llama_prompt: Llama 3でプロンプトを生成するか（Falseの場合は直接使用）
        """
        # Llama 3でプロンプト生成
        if use_llama_prompt:
            prompt_data = await self.generate_prompt(user_request, style=style)
            prompt = prompt_data["prompt"]
            negative_prompt = prompt_data["negative_prompt"]
        else:
            prompt = f"{user_request}, highly detailed, 4k, professional photography"
            negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
        
        # Stable Diffusionで画像生成
        self.initialize_sd()
        
        print(f"\n{'='*60}")
        print(f"Stable Diffusionで画像生成中...")
        print(f"{'='*60}\n")
        
        images = self.sd_generator.generate(  # type: ignore[union-attr]
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            output_dir=output_dir
        )
        
        return images
    
    def cleanup(self):
        """メモリのクリーンアップ"""
        if self.sd_generator:
            self.sd_generator.cleanup()


async def main():
    """メイン関数"""
    print("=" * 60)
    print("Llama 3 Guru Uncensored + Stable Diffusion")
    print("統合画像生成システム")
    print("=" * 60)
    
    # 生成器の初期化
    generator = Llama3GuruImageGenerator(
        llama_model="gurubot/llama3-guru-uncensored:latest",
        sd_model_id="runwayml/stable-diffusion-v1-5"
    )
    
    # 接続確認
    print("\n接続確認中...")
    if not await generator.check_llama_connection():
        print("❌ Llama 3への接続に失敗しました")
        print("\n利用可能なモデルを確認中...")
        models = await generator.list_available_models()
        if models:
            print("利用可能なモデル:")
            for model in models:
                print(f"  - {model}")
            print("\nヒント: llama_modelパラメータを上記のモデル名に変更してください")
        return
    
    print("✅ Llama 3への接続成功")
    
    # 利用可能なモデルを表示
    models = await generator.list_available_models()
    if models:
        print(f"\n利用可能なモデル: {len(models)}個")
        for model in models:
            if "llama" in model.lower() or "guru" in model.lower():
                print(f"  ✅ {model} (使用中)")
            else:
                print(f"  - {model}")
    
    try:
        # サンプル画像生成
        print("\n" + "=" * 60)
        print("サンプル画像生成")
        print("=" * 60)
        
        # 例1: 風景画像
        await generator.generate_image(
            user_request="美しい山と湖の風景、夕日、高品質",
            style="detailed",
            width=512,
            height=512,
            num_inference_steps=30,
            guidance_scale=7.5
        )
        
        # 例2: ポートレート
        # await generator.generate_image(
        #     user_request="美しい女性のポートレート、プロフェッショナルな写真",
        #     style="realistic",
        #     width=512,
        #     height=768,
        #     num_inference_steps=40
        # )
        
    except KeyboardInterrupt:
        print("\n\n生成が中断されました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.cleanup()
    
    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

