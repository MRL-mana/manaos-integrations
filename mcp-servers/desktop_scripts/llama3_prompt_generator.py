# -*- coding: utf-8 -*-
"""
Llama 3 Guru Uncensored プロンプト生成ツール
画像生成用のプロンプトを生成します
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime
from local_llm_helper_simple import LocalLLM


class Llama3PromptGenerator:
    """Llama 3でプロンプトを生成するクラス"""
    
    def __init__(self, model: str = "gurubot/llama3-guru-uncensored:latest"):
        self.llm = LocalLLM(default_model=model)
        self.model = model
    
    async def generate_prompt(
        self,
        user_request: str,
        style: str = "detailed",
        timeout: int = 300
    ) -> dict:
        """プロンプトを生成"""
        system_prompt = """You are an expert at creating prompts for image generation.
Generate a high-quality prompt for Stable Diffusion based on the user's request.

Requirements:
- Write in English
- Include specific and detailed descriptions
- Add quality keywords (highly detailed, 4k, professional photography, masterpiece, best quality)
- Use comma-separated format
- Style: {style}

Negative prompt should include:
- blurry, low quality, distorted, ugly, bad anatomy, bad proportions
- Other unwanted elements if applicable

Output format:
Prompt: [generated prompt]
Negative Prompt: [negative prompt]""".format(style=style)
        
        user_prompt = f"""User request: {user_request}
Style: {style}

Generate a Stable Diffusion prompt based on the above request."""
        
        print(f"\nGenerating prompt for: {user_request}")
        print(f"Style: {style}")
        print("-" * 60)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # タイムアウト設定（デフォルト5分）
        import asyncio
        try:
            response = await asyncio.wait_for(
                self.llm.chat(messages, model=self.model),
                timeout=300  # 5分
            )
        except asyncio.TimeoutError:
            raise TimeoutError("プロンプト生成がタイムアウトしました（300秒）")
        
        # レスポンスからプロンプトを抽出
        prompt = ""
        negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions"
        
        lines = response.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('Prompt:') or line.startswith('プロンプト:'):
                prompt = line.split(':', 1)[1].strip()
            elif line.startswith('Negative Prompt:') or line.startswith('ネガティブプロンプト:'):
                negative_prompt = line.split(':', 1)[1].strip()
        
        # プロンプトが見つからない場合、レスポンス全体を使用
        if not prompt:
            # 最初の長い文をプロンプトとして使用
            prompt = response.strip()
            # 最初の2-3文をプロンプトとして使用
            sentences = prompt.split('.')
            if len(sentences) > 2:
                prompt = '. '.join(sentences[:2]) + '.'
        
        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "raw_response": response
        }
    
    async def save_prompt(self, prompt_data: dict, output_file: str = None):  # type: ignore
        """プロンプトをファイルに保存"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"prompt_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] Prompt saved to: {output_file}")
        return output_file


async def interactive_mode():
    """インタラクティブモード"""
    print("=" * 60)
    print("Llama 3 Guru Uncensored Prompt Generator")
    print("Interactive Mode")
    print("=" * 60)
    print("\nType 'quit' or 'exit' to exit\n")
    
    generator = Llama3PromptGenerator()
    
    # 接続確認
    if not await generator.llm.check_connection():
        print("[ERROR] Failed to connect to Ollama")
        return
    
    print("[OK] Connected to Ollama")
    print(f"Model: {generator.model}\n")
    
    try:
        while True:
            user_request = input("Enter image request: ").strip()
            
            if not user_request:
                continue
            
            if user_request.lower() in ['quit', 'exit', 'q']:
                print("\nExiting...")
                break
            
            style = input("Style [detailed]: ").strip() or "detailed"
            
            try:
                prompt_data = await generator.generate_prompt(user_request, style=style)
                
                print("\n" + "=" * 60)
                print("Generated Prompt:")
                print("=" * 60)
                print(prompt_data['prompt'])
                print("\nNegative Prompt:")
                print(prompt_data['negative_prompt'])
                print("=" * 60)
                
                save = input("\nSave to file? (y/N): ").strip().lower()
                if save == 'y':
                    await generator.save_prompt(prompt_data)
                
            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"[ERROR] {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Llama 3 Guru Uncensored Prompt Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python llama3_prompt_generator.py
  
  # Generate prompt
  python llama3_prompt_generator.py "beautiful landscape"
  
  # With style
  python llama3_prompt_generator.py "portrait" --style realistic --save
        """
    )
    
    parser.add_argument(
        "request",
        nargs="?",
        help="Image generation request"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gurubot/llama3-guru-uncensored:latest",
        help="Llama model name"
    )
    
    parser.add_argument(
        "--style",
        type=str,
        default="detailed",
        help="Style (detailed, artistic, realistic, anime, etc.)"
    )
    
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save prompt to file"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    # インタラクティブモード
    if not args.request:
        await interactive_mode()
        return
    
    # 直接生成モード
    generator = Llama3PromptGenerator(model=args.model)
    
    # 接続確認
    if not await generator.llm.check_connection():
        print("[ERROR] Failed to connect to Ollama")
        sys.exit(1)
    
    try:
        prompt_data = await generator.generate_prompt(args.request, style=args.style)
        
        print("\n" + "=" * 60)
        print("Generated Prompt:")
        print("=" * 60)
        print(prompt_data['prompt'])
        print("\nNegative Prompt:")
        print(prompt_data['negative_prompt'])
        print("=" * 60)
        
        if args.save or args.output:
            await generator.save_prompt(prompt_data, args.output)
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

