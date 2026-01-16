# LTX-2 クイックスタートガイド

## セットアップ完了後の使用方法

### 1. 動作確認

```powershell
# テストスクリプトを実行
python test_ltx2.py
```

### 2. シンプルな動画生成

```powershell
# 基本的な使用方法
python ltx2_example_simple_video.py "path/to/image.png"

# オプション指定
python ltx2_example_simple_video.py "image.png" --prompt "a beautiful sunset" --length 10

# キュー状態も確認
python ltx2_example_simple_video.py "image.png" --check-queue
```

### 3. API経由で使用

#### Pythonスクリプトから

```python
import requests

# 動画生成をリクエスト
response = requests.post("http://localhost:9500/api/ltx2/generate", json={
    "start_image_path": "path/to/image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "negative_prompt": "blurry, low quality",
    "video_length_seconds": 5,
    "use_two_pass": True,
    "use_nag": True,
    "use_res2s_sampler": True
})

result = response.json()
prompt_id = result["prompt_id"]
print(f"動画生成開始: {prompt_id}")

# 状態確認
status = requests.get(f"http://localhost:9500/api/ltx2/status/{prompt_id}").json()
print(status)
```

#### curlから

```bash
# 動画生成
curl -X POST http://localhost:9500/api/ltx2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_path": "path/to/image.png",
    "prompt": "a beautiful landscape",
    "video_length_seconds": 5,
    "use_two_pass": true,
    "use_nag": true,
    "use_res2s_sampler": true
  }'

# キュー状態確認
curl http://localhost:9500/api/ltx2/queue

# 履歴確認
curl http://localhost:9500/api/ltx2/history?max_items=10
```

### 4. Pythonモジュールとして使用

```python
from ltx2_video_integration import LTX2VideoIntegration

# 初期化
ltx2 = LTX2VideoIntegration()

# 動画生成
prompt_id = ltx2.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    negative_prompt="blurry, low quality",
    video_length_seconds=5,
    use_two_pass=True,  # 推奨
    use_nag=True,  # 推奨
    use_res2s_sampler=True,  # 推奨
    model_name="ltx2-q8.gguf"
)

if prompt_id:
    print(f"生成開始: {prompt_id}")
    
    # キュー状態確認
    queue = ltx2.get_queue_status()
    print(f"キュー: {queue}")
    
    # 履歴確認
    history = ltx2.get_history(max_items=10)
    print(f"履歴: {len(history)}件")
```

## 推奨設定

Super LTX-2設定の推奨パラメータ：

```python
{
    "use_two_pass": True,      # 2段階生成（推奨）
    "use_nag": True,           # NAG使用（推奨）
    "use_res2s_sampler": True, # res_2sサンプラー（推奨）
    "model_name": "ltx2-q8.gguf"  # Q8 GGUFモデル（推奨）
}
```

## よくある使用例

### 風景動画を生成

```python
python ltx2_example_simple_video.py "landscape.png" \
  --prompt "a beautiful landscape, mountains, sunset, cinematic" \
  --length 10
```

### 人物動画を生成

```python
python ltx2_example_simple_video.py "person.png" \
  --prompt "a person walking, smooth motion, natural movement" \
  --negative-prompt "jittery, unnatural, distorted"
```

### アニメ風動画を生成

```python
python ltx2_example_simple_video.py "anime.png" \
  --prompt "anime style, vibrant colors, smooth animation" \
  --length 8
```

## トラブルシューティング

### APIサーバーに接続できない

1. `unified_api_server.py`が起動しているか確認
2. ポート9500が正しいか確認
3. ファイアウォールの設定を確認

### 動画生成が失敗する

1. ComfyUIが起動しているか確認: http://localhost:8188
2. LTX-2モデルが配置されているか確認: `C:\ComfyUI\models\unet\`
3. VRAMが十分か確認（8GB〜推奨）
4. ComfyUIのログを確認

### カスタムノードが見つからない

1. ComfyUIを再起動（カスタムノードを読み込むため）
2. カスタムノードがインストールされているか確認
3. 手動で再インストール: `python install_ltx2_custom_nodes.py`

## 次のステップ

1. 実際の画像でテスト
2. パラメータを調整して最適化
3. バッチ処理の実装（複数の動画生成）
4. ワークフローのカスタマイズ

## 参考資料

- **README**: `LTX2_README.md`
- **統合計画書**: `LTX2_INTEGRATION_PLAN.md`
- **セットアップ完了報告**: `LTX2_SETUP_COMPLETE.md`
- **参考記事**: https://note.com/ai_hakase/n/n01d2855d90cd
