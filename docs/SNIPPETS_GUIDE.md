# ManaOS スニペット活用ガイド

このガイドでは、ManaOSの開発に役立つコードスニペットを紹介します。

## 目次
1. [サービス統合](#サービス統合)
2. [メモリ操作](#メモリ操作)
3. [LLMルーティング](#llmルーティング)
4. [画像生成](#画像生成)
5. [エラーハンドリング](#エラーハンドリング)

---

## サービス統合

### 設定ローダーの使用

```python
from config_loader import get_port, get_service_url, check_port_conflicts

# ポート番号を取得
unified_api_port = get_port('unified_api')  # 9502

# サービスURLを取得
url = get_service_url('mrl_memory')  # http://127.0.0.1:5105

# ポート衝突をチェック
conflicts = check_port_conflicts()
if conflicts:
    print(f"警告: ポート衝突検出 {conflicts}")
```

### サービスヘルスチェック

```python
import requests
from config_loader import get_service_url

def check_service_health(service_name: str) -> bool:
    """サービスの健全性をチェック"""
    try:
        url = f"{get_service_url(service_name)}/health"
        response = requests.get(url, timeout=3)
        return response.status_code == 200
    except:
        return False

# 使用例
if check_service_health('unified_api'):
    print("✅ Unified API is healthy")
```

---

## メモリ操作

### メモリ保存

```python
import requests
from config_loader import get_service_url

def store_memory(content: str, context: str = "general"):
    """MRLメモリに情報を保存"""
    url = f"{get_service_url('mrl_memory', 'manaos_services')}/store"
    
    payload = {
        "content": content,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 使用例
result = store_memory("重要な情報", context="user_preferences")
print(f"メモリID: {result['memory_id']}")
```

### メモリ検索

```python
def search_memory(query: str, limit: int = 5):
    """MRLメモリから情報を検索"""
    url = f"{get_service_url('mrl_memory', 'manaos_services')}/search"
    
    params = {
        "query": query,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    return response.json()['results']

# 使用例
memories = search_memory("ユーザー設定")
for memory in memories:
    print(f"- {memory['content']} (relevance: {memory['score']})")
```

---

## LLMルーティング

### 最適なモデルを選択

```python
def route_llm_request(prompt: str, difficulty: str = "auto"):
    """LLMルーティングで最適なモデルを選択"""
    url = f"{get_service_url('llm_routing', 'manaos_services')}/route"
    
    payload = {
        "prompt": prompt,
        "difficulty": difficulty,  # auto, simple, moderate, complex
        "preferences": {
            "speed_priority": True,
            "local_only": False
        }
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 使用例
result = route_llm_request("簡単な要約を生成してください")
print(f"選択モデル: {result['model']}")
print(f"推論時間: {result['inference_time']}ms")
```

### ストリーミング応答

```python
def stream_llm_response(prompt: str, model: str = "auto"):
    """LLMからストリーミング応答を取得"""
    url = f"{get_service_url('llm_routing', 'manaos_services')}/stream"
    
    payload = {"prompt": prompt, "model": model}
    
    with requests.post(url, json=payload, stream=True) as response:
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                yield chunk

# 使用例
for token in stream_llm_response("物語を書いて"):
    print(token, end='', flush=True)
```

---

## 画像生成

### ComfyUI経由で画像生成

```python
def generate_image_comfyui(prompt: str, negative: str = "", size: tuple = (512, 512)):
    """ComfyUI経由で画像を生成"""
    url = f"{get_service_url('unified_api')}/generate_image"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "width": size[0],
        "height": size[1],
        "backend": "comfyui",
        "steps": 20,
        "cfg_scale": 7.5
    }
    
    response = requests.post(url, json=payload)
    return response.json()['image_url']

# 使用例
image_url = generate_image_comfyui(
    prompt="beautiful landscape, sunset, mountains",
    negative="blurry, low quality"
)
print(f"生成完了: {image_url}")
```

### ギャラリーに保存

```python
def save_to_gallery(image_path: str, tags: list, rating: int = 0):
    """生成画像をギャラリーに保存"""
    url = f"{get_service_url('gallery_api')}/images"
    
    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {
            'tags': ','.join(tags),
            'rating': rating
        }
        
        response = requests.post(url, files=files, data=data)
        return response.json()

# 使用例
result = save_to_gallery(
    "output/image_001.png",
    tags=["landscape", "sunset", "ai-generated"],
    rating=5
)
print(f"ギャラリーID: {result['image_id']}")
```

---

## エラーハンドリング

### リトライデコレーター

```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1, backoff=2):
    """リトライ機能付きデコレーター"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    
                    print(f"リトライ {attempts}/{max_attempts} - {current_delay}秒待機")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator

# 使用例
@retry(max_attempts=5, delay=2)
def unreliable_api_call():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()
```

### サービスフォールバック

```python
def call_with_fallback(primary_service: str, fallback_service: str, endpoint: str, **kwargs):
    """プライマリサービスが失敗した場合にフォールバック"""
    services = [primary_service, fallback_service]
    
    for service in services:
        try:
            url = f"{get_service_url(service)}{endpoint}"
            response = requests.post(url, json=kwargs, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"{service} 失敗: {e}")
            if service == services[-1]:
                raise
    
# 使用例
result = call_with_fallback(
    primary_service='unified_api',
    fallback_service='direct_llm',
    endpoint='/generate',
    prompt="Hello, world!"
)
```

---

## 便利なユーティリティ

### サービス状態監視

```python
import asyncio

async def monitor_services(interval: int = 30):
    """定期的にサービス状態を監視"""
    from config_loader import get_all_services
    
    while True:
        services = get_all_services()
        status = {}
        
        for name, info in services.items():
            is_healthy = check_service_health(name)
            status[name] = "✅" if is_healthy else "❌"
        
        print("\n=== サービス状態 ===")
        for name, state in status.items():
            print(f"{state} {name}")
        
        await asyncio.sleep(interval)

# 使用例（非同期実行）
asyncio.run(monitor_services(interval=60))
```

### バッチ処理ヘルパー

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_batch(items: list, processor_func, max_workers: int = 5):
    """アイテムを並列バッチ処理"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(processor_func, item): item for item in items}
        
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✅ {item} 処理完了")
            except Exception as e:
                print(f"❌ {item} 処理失敗: {e}")
    
    return results

# 使用例
def process_image(image_path):
    # 画像処理ロジック
    return analyze_image(image_path)

results = process_batch(
    items=['img1.png', 'img2.png', 'img3.png'],
    processor_func=process_image,
    max_workers=3
)
```

---

## 関連リンク

- [MCPサーバーガイド](./MCP_SERVERS_GUIDE.md)
- [起動依存関係](./STARTUP_DEPENDENCY.md)
- [スキルとMCP統合](./SKILLS_AND_MCP_GUIDE.md)
