# LTX-2 使用例集

## 基本的な使用方法

### 1. シンプルな動画生成

```powershell
# 基本的な使用方法
python ltx2_example_simple_video.py "path/to/image.png"

# カスタムプロンプト指定
python ltx2_example_simple_video.py "image.png" --prompt "a beautiful sunset over mountains"

# 動画長を変更
python ltx2_example_simple_video.py "image.png" --length 10

# キュー状態も確認
python ltx2_example_simple_video.py "image.png" --check-queue
```

### 2. バッチ動画生成

```powershell
# 複数の画像から動画を生成
python ltx2_batch_example.py "image1.png" "image2.png" "image3.png"

# カスタムプロンプト指定
python ltx2_batch_example.py "img1.png" "img2.png" --prompt "cinematic landscape"

# 遅延時間を調整
python ltx2_batch_example.py "img1.png" "img2.png" --delay 3.0
```

## Pythonスクリプトから使用

### シンプルな動画生成

```python
from ltx2_video_integration import LTX2VideoIntegration

ltx2 = LTX2VideoIntegration()

prompt_id = ltx2.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    negative_prompt="blurry, low quality",
    video_length_seconds=5,
    use_two_pass=True,
    use_nag=True,
    use_res2s_sampler=True
)

if prompt_id:
    print(f"生成開始: {prompt_id}")
```

### バッチ処理

```python
from ltx2_video_integration import LTX2VideoIntegration
from pathlib import Path

ltx2 = LTX2VideoIntegration()

# フォルダ内の画像を処理
image_folder = Path("images")
image_files = list(image_folder.glob("*.png"))

prompt_ids = []
for image_file in image_files:
    prompt_id = ltx2.generate_video(
        start_image_path=str(image_file),
        prompt="a beautiful landscape",
        use_two_pass=True,
        use_nag=True,
        use_res2s_sampler=True
    )
    if prompt_id:
        prompt_ids.append(prompt_id)

print(f"生成開始: {len(prompt_ids)}件")
```

## API経由で使用

### curlから

```bash
# 動画生成
curl -X POST http://localhost:9500/api/ltx2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_path": "path/to/image.png",
    "prompt": "a beautiful landscape",
    "negative_prompt": "blurry, low quality",
    "video_length_seconds": 5,
    "use_two_pass": true,
    "use_nag": true,
    "use_res2s_sampler": true
  }'

# キュー状態確認
curl http://localhost:9500/api/ltx2/queue

# 履歴確認
curl http://localhost:9500/api/ltx2/history?max_items=10

# 状態確認
curl http://localhost:9500/api/ltx2/status/<prompt_id>
```

### Python requestsから

```python
import requests

# 動画生成
response = requests.post("http://localhost:9500/api/ltx2/generate", json={
    "start_image_path": "image.png",
    "prompt": "a beautiful landscape",
    "negative_prompt": "blurry, low quality",
    "video_length_seconds": 5,
    "use_two_pass": True,
    "use_nag": True,
    "use_res2s_sampler": True
})

result = response.json()
prompt_id = result["prompt_id"]

# 状態確認
status = requests.get(f"http://localhost:9500/api/ltx2/status/{prompt_id}").json()
print(status)
```

## よくある使用パターン

### パターン1: 風景動画を生成

```python
python ltx2_example_simple_video.py "landscape.png" \
  --prompt "a beautiful landscape, mountains, sunset, cinematic, highly detailed" \
  --negative-prompt "blurry, low quality, distorted, artifacts" \
  --length 10
```

### パターン2: 人物動画を生成

```python
python ltx2_example_simple_video.py "person.png" \
  --prompt "a person walking, smooth motion, natural movement, cinematic" \
  --negative-prompt "jittery, unnatural, distorted, artifacts"
```

### パターン3: アニメ風動画を生成

```python
python ltx2_example_simple_video.py "anime.png" \
  --prompt "anime style, vibrant colors, smooth animation, highly detailed" \
  --length 8
```

### パターン4: フォルダ内の画像を一括処理

```python
from pathlib import Path
from ltx2_example_simple_video import generate_simple_video

image_folder = Path("input_images")
for image_file in image_folder.glob("*.png"):
    prompt_id = generate_simple_video(
        start_image_path=str(image_file),
        prompt="a beautiful landscape",
        use_two_pass=True,
        use_nag=True,
        use_res2s_sampler=True
    )
    if prompt_id:
        print(f"✅ {image_file.name}: {prompt_id}")
```

## 推奨設定

### Super LTX-2設定（推奨）

```python
{
    "use_two_pass": True,      # 2段階生成（推奨）
    "use_nag": True,           # NAG使用（推奨）
    "use_res2s_sampler": True, # res_2sサンプラー（推奨）
    "model_name": "ltx2-q8.gguf"  # Q8 GGUFモデル（推奨）
}
```

### 高速生成設定（品質優先度：中）

```python
{
    "use_two_pass": False,     # 1パス生成（高速）
    "use_nag": True,           # NAG使用（推奨）
    "use_res2s_sampler": False # 通常サンプラー（高速）
}
```

### 最高品質設定（速度優先度：低）

```python
{
    "use_two_pass": True,      # 2段階生成
    "use_nag": True,           # NAG使用
    "use_res2s_sampler": True, # res_2sサンプラー
    "steps": 50,               # ステップ数を増やす（オプション）
    "pass2_width": 1024,       # アップスケール解像度（オプション）
    "pass2_height": 1024       # アップスケール解像度（オプション）
}
```

## トラブルシューティング

### APIサーバーに接続できない

1. `unified_api_server.py`が起動しているか確認
2. ポート9500が正しいか確認
3. ファイアウォールの設定を確認

### 動画生成が失敗する

1. ComfyUIが起動しているか確認: http://localhost:8188
2. LTX-2モデルが配置されているか確認
3. VRAMが十分か確認（8GB〜推奨）
4. ComfyUIのログを確認

### 生成速度が遅い

1. `use_two_pass`を`False`に設定（1パス生成）
2. `use_res2s_sampler`を`False`に設定（通常サンプラー）
3. VRAMを確認（不足している場合は使用量を減らす）

## 参考資料

- **README**: `LTX2_README.md`
- **クイックスタートガイド**: `ltx2_quick_start_guide.md`
- **統合計画書**: `LTX2_INTEGRATION_PLAN.md`
- **セットアップ完了報告**: `LTX2_SETUP_COMPLETE.md`
- **参考記事**: https://note.com/ai_hakase/n/n01d2855d90cd
