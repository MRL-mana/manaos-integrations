#!/usr/bin/env python3
"""
GPT-OSS-20B量子化版ダウンロードスクリプト
"""

import os
import sys
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def download_quantized_gpt_oss_20b():
    """GPT-OSS-20B量子化版をダウンロード"""
    
    # 量子化版モデル名（実際のリリース後に正しいモデル名に更新）
    model_name = "microsoft/gpt-oss-20b-4bit"  # 仮のモデル名
    
    print(f"GPT-OSS-20B量子化版をダウンロード中: {model_name}")
    
    try:
        # トークナイザーをダウンロード
        print("トークナイザーをダウンロード中...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained("./gpt-oss-20b-quantized")
        
        # 量子化版モデルをダウンロード
        print("量子化版モデルをダウンロード中...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            load_in_4bit=True,  # 4bit量子化
            bnb_4bit_compute_dtype=torch.float16
        )
        model.save_pretrained("./gpt-oss-20b-quantized")
        
        print("✅ GPT-OSS-20B量子化版のダウンロードが完了しました！")
        return True
        
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        print("モデルがまだリリースされていない可能性があります")
        return False

def create_quantized_inference_script():
    """量子化版推論用スクリプトを作成"""
    
    script_content = '''#!/usr/bin/env python3
"""
GPT-OSS-20B量子化版推論スクリプト
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import BitsAndBytesConfig

def load_quantized_model():
    """量子化版モデルを読み込み"""
    model_path = "./gpt-oss-20b-quantized"
    
    print("量子化版モデルを読み込み中...")
    
    # 4bit量子化設定
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
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
    tokenizer, model = load_quantized_model()
    
    while True:
        user_input = input("\\n質問を入力してください (終了: 'quit'): ")
        if user_input.lower() == 'quit':
            break
            
        response = generate_response(user_input, tokenizer, model)
        print(f"\\n回答: {response}")
'''
    
    with open("./inference_quantized.py", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ 量子化版推論スクリプトを作成しました: inference_quantized.py")

if __name__ == "__main__":
    success = download_quantized_gpt_oss_20b()
    if success:
        create_quantized_inference_script()
