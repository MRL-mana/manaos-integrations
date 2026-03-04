#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioモデルの使用可能性をテスト"""

import sys
import os
import requests

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

def _test_model_availability(model_name: str, timeout: int = 30) -> bool:
    """
    モデルが実際に使用可能かテスト
    
    Args:
        model_name: モデル名
        timeout: タイムアウト秒数
    
    Returns:
        使用可能な場合True
    """
    try:
        url = "http://127.0.0.1:1234/v1/chat/completions"
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 5,
            "temperature": 0.7
        }
        response = requests.post(url, json=data, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def get_available_models() -> list:
    """
    使用可能なモデルのリストを取得
    
    Returns:
        使用可能なモデル名のリスト
    """
    available = []
    
    try:
        r = requests.get('http://127.0.0.1:1234/v1/models', timeout=5)
        if r.status_code == 200:
            models_data = r.json().get('data', [])
            model_names = [model.get('id', '') for model in models_data]
            
            # 優先順位順にテスト
            preferred_models = [
                "qwen2.5-coder-32b-instruct",
                "qwen/qwen2.5-coder-14b-instruct",
                "qwen2.5-coder-14b-instruct",
                "openai/gpt-oss-20b",
                "qwen2.5-coder-7b-instruct",
            ]
            
            # 問題のあるモデルをスキップ
            skip_models = ["ggml-org/qwen2.5-coder-14b-instruct"]
            
            for preferred in preferred_models:
                for model_name in model_names:
                    # スキップ対象を除外
                    if any(skip in model_name.lower() for skip in skip_models):
                        continue
                    # 部分一致で検索
                    if preferred.lower() in model_name.lower() or model_name.lower() in preferred.lower():
                        # 実際に使用可能かテスト
                        if _test_model_availability(model_name, timeout=30):
                            if model_name not in available:
                                available.append(model_name)
                            break
    except Exception:
        pass
    
    return available


