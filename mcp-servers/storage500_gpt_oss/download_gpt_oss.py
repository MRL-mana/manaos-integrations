#!/usr/bin/env python3
"""
GPT-OSS-20Bモデルダウンロードスクリプト
"""

import os
import sys
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, AutoModelForCausalLM

def download_gpt_oss_20b():
    """GPT-OSS-20Bモデルをダウンロード"""
    
    # モデル名（実際のリリース後に正しいモデル名に更新）
    model_name = "microsoft/gpt-oss-20b"  # 仮のモデル名
    
    print(f"GPT-OSS-20Bモデルをダウンロード中: {model_name}")
    
    try:
        # モデルとトークナイザーをダウンロード
        print("トークナイザーをダウンロード中...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained("./gpt-oss-20b")
        
        print("モデルをダウンロード中...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
        model.save_pretrained("./gpt-oss-20b")
        
        print("✅ GPT-OSS-20Bモデルのダウンロードが完了しました！")
        return True
        
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        print("モデルがまだリリースされていない可能性があります")
        return False

def create_inference_script():
    """推論用スクリプトを作成"""
    
    script_content = '''#!/usr/bin/env python3
"""
GPT-OSS-20B推論スクリプト
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def load_model():
    """モデルを読み込み"""
    model_path = "./gpt-oss-20b"
    
    print("モデルを読み込み中...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    return tokenizer, model

def generate_response(prompt, tokenizer, model, max_length=512):
    """テキスト生成"""
    inputs = tokenizer(prompt, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

if __name__ == "__main__":
    tokenizer, model = load_model()
    
    while True:
        user_input = input("\\n質問を入力してください (終了: 'quit'): ")
        if user_input.lower() == 'quit':
            break
            
        response = generate_response(user_input, tokenizer, model)
        print(f"\\n回答: {response}")
'''
    
    with open("./inference.py", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ 推論スクリプトを作成しました: inference.py")

if __name__ == "__main__":
    success = download_gpt_oss_20b()
    if success:
        create_inference_script()
