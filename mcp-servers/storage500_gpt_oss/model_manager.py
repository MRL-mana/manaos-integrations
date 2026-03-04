#!/usr/bin/env python3
"""
GPT-OSS-20Bモデル管理スクリプト
通常版と量子化版を状況に応じて使い分け
"""

import os
import psutil
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import BitsAndBytesConfig

class GPTOSSManager:
    def __init__(self):
        self.normal_model_path = "./gpt-oss-20b"
        self.quantized_model_path = "./gpt-oss-20b-quantized"
        self.tokenizer = None
        self.model = None
        self.model_type = None
    
    def check_memory(self):
        """利用可能メモリをチェック"""
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        print(f"利用可能メモリ: {available_gb:.1f}GB")
        return available_gb
    
    def load_model(self, force_quantized=False):
        """メモリ状況に応じてモデルを読み込み"""
        available_gb = self.check_memory()
        
        if force_quantized or available_gb < 16:
            print("🔄 量子化版モデルを読み込み中...")
            return self.load_quantized_model()
        else:
            print("🔄 通常版モデルを読み込み中...")
            return self.load_normal_model()
    
    def load_normal_model(self):
        """通常版モデルを読み込み"""
        if not os.path.exists(self.normal_model_path):
            print("❌ 通常版モデルが見つかりません")
            return False
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.normal_model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.normal_model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            self.model_type = "normal"
            print("✅ 通常版モデルを読み込みました")
            return True
        except Exception as e:
            print(f"❌ 通常版モデル読み込みエラー: {e}")
            return False
    
    def load_quantized_model(self):
        """量子化版モデルを読み込み"""
        if not os.path.exists(self.quantized_model_path):
            print("❌ 量子化版モデルが見つかりません")
            return False
        
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.quantized_model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.quantized_model_path,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True
            )
            self.model_type = "quantized"
            print("✅ 量子化版モデルを読み込みました")
            return True
        except Exception as e:
            print(f"❌ 量子化版モデル読み込みエラー: {e}")
            return False
    
    def generate_response(self, prompt, max_length=512):
        """テキスト生成"""
        if self.model is None or self.tokenizer is None:
            print("❌ モデルが読み込まれていません")
            return None
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
        except Exception as e:
            print(f"❌ 生成エラー: {e}")
            return None
    
    def get_model_info(self):
        """モデル情報を取得"""
        if self.model is None:
            return "モデル未読み込み"
        
        info = f"モデルタイプ: {self.model_type}"
        if self.model_type == "quantized":
            info += " (4bit量子化)"
        
        # メモリ使用量を表示
        memory = psutil.virtual_memory()
        used_gb = memory.used / (1024**3)
        total_gb = memory.total / (1024**3)
        info += f" | メモリ使用量: {used_gb:.1f}GB / {total_gb:.1f}GB"
        
        return info

def main():
    """メイン関数"""
    manager = GPTOSSManager()
    
    print("🤖 GPT-OSS-20Bモデル管理システム")
    print("=" * 50)
    
    # モデルを読み込み
    if not manager.load_model():
        print("❌ モデルの読み込みに失敗しました")
        return
    
    print(f"📊 {manager.get_model_info()}")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n質問を入力してください (終了: 'quit', モデル切り替え: 'switch'): ")
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'switch':
                # モデルを切り替え
                if manager.model_type == "normal":
                    print("🔄 量子化版に切り替え中...")
                    manager.load_quantized_model()
                else:
                    print("🔄 通常版に切り替え中...")
                    manager.load_normal_model()
                print(f"📊 {manager.get_model_info()}")
                continue
            elif user_input.strip() == "":
                continue
            
            print("🤔 生成中...")
            response = manager.generate_response(user_input)
            
            if response:
                print(f"\n💬 回答: {response}")
            else:
                print("❌ 回答の生成に失敗しました")
                
        except KeyboardInterrupt:
            print("\n👋 終了します")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
