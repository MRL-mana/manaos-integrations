# SVI × Wan 2.2 動画生成統合ガイド

## 概要

ManaOSに統合された「SVI × Wan 2.2」動画生成機能の使用方法を説明します。

この機能により、ComfyUIを使用して理論上無限の長さの高品質な動画を生成できます。エラーリサイクル学習により、長尺生成でも品質を維持し、ストーリー性のある長編動画の制作が可能です。

---

## 前提条件

### 必要な環境

1. **ComfyUI**: ローカルまたはクラウド環境で起動していること
   - デフォルトURL: `http://127.0.0.1:8188`
   - 環境変数 `COMFYUI_URL` で変更可能

2. **SVI × Wan 2.2ワークフロー**: ComfyUIにインストールされていること
   - ワークフローノードが利用可能である必要があります
   - モデルファイル（wan2.2.safetensors）が準備されていること

3. **ManaOS統合APIサーバー**: 起動していること
   - デフォルトURL: `http://127.0.0.1:9502`
   - 環境変数 `MANAOS_INTEGRATION_PORT` で変更可能

---

## 基本的な使用方法

### 1. Pythonモジュールから直接使用

```python
from svi_wan22_video_integration import SVIWan22VideoIntegration

# 初期化
svi = SVIWan22VideoIntegration(base_url="http://127.0.0.1:8188")

# 利用可能か確認
if not svi.is_available():
    print("ComfyUIが利用できません")
    exit(1)

# 動画生成
prompt_id = svi.generate_video(
    start_image_path="path/to/start_image.png",
    prompt="a beautiful landscape, mountains, sunset",
    video_length_seconds=5,
    steps=6,
    motion_strength=1.3,
    sage_attention=True
)

if prompt_id:
    print(f"動画生成が開始されました: {prompt_id}")
else:
    print("動画生成に失敗しました")
```

### 2. REST API経由で使用

#### 動画生成

```bash
curl -X POST http://127.0.0.1:9502/api/svi/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_path": "path/to/start_image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "video_length_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3,
    "sage_attention": true
  }'
```

#### 動画延長

```bash
curl -X POST http://127.0.0.1:9502/api/svi/extend \
  -H "Content-Type: application/json" \
  -d '{
    "previous_video_path": "path/to/previous_video.mp4",
    "prompt": "continue the scene with more action",
    "extend_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3
  }'
```

#### ストーリー動画生成

```bash
curl -X POST http://127.0.0.1:9502/api/svi/story \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_path": "path/to/start_image.png",
    "story_prompts": [
      {"timestamp": 0, "prompt": "smiling face"},
      {"timestamp": 5, "prompt": "sad face"},
      {"timestamp": 10, "prompt": "surprised face"}
    ],
    "segment_length_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3
  }'
```

### 3. ManaOSコアAPI経由で使用

```python
from manaos_integrations.manaos_core_api import act

# 動画生成
result = act("generate_video", {
    "start_image_path": "path/to/start_image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "video_length_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3,
    "sage_attention": True
})

print(f"実行ID: {result.get('prompt_id')}")

# 動画延長
result = act("extend_video", {
    "previous_video_path": "path/to/previous_video.mp4",
    "prompt": "continue the scene",
    "extend_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3
})

# ストーリー動画生成
result = act("create_story_video", {
    "start_image_path": "path/to/start_image.png",
    "story_prompts": [
        {"timestamp": 0, "prompt": "smiling face"},
        {"timestamp": 5, "prompt": "sad face"}
    ],
    "segment_length_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3
})
```

---

## パラメータ詳細

### generate_video パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `start_image_path` | str | 必須 | 開始画像のパス |
| `prompt` | str | 必須 | プロンプト（日本語可、自動翻訳） |
| `video_length_seconds` | int | 5 | 動画の長さ（秒） |
| `steps` | int | 6 | ステップ数（6-12推奨） |
| `motion_strength` | float | 1.3 | モーション強度（1.3-1.5推奨） |
| `sage_attention` | bool | True | Sage Attentionを有効にするか |
| `extend_enabled` | bool | False | Extend機能を有効にするか |
| `timestamped_prompts` | dict | None | タイムスタンプ付きプロンプト（オプション） |

### extend_video パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `previous_video_path` | str | 必須 | 前の動画のパス |
| `prompt` | str | 必須 | 延長部分のプロンプト |
| `extend_seconds` | int | 5 | 延長する秒数 |
| `steps` | int | 6 | ステップ数 |
| `motion_strength` | float | 1.3 | モーション強度 |

### create_story_video パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `start_image_path` | str | 必須 | 開始画像のパス |
| `story_prompts` | list | 必須 | ストーリープロンプトのリスト |
| `segment_length_seconds` | int | 5 | 各セグメントの長さ（秒） |
| `steps` | int | 6 | ステップ数 |
| `motion_strength` | float | 1.3 | モーション強度 |

---

## 推奨設定

### 品質重視

```python
svi.generate_video(
    start_image_path="image.png",
    prompt="your prompt",
    video_length_seconds=5,
    steps=12,  # 高品質
    motion_strength=1.3,
    sage_attention=True
)
```

### 速度重視

```python
svi.generate_video(
    start_image_path="image.png",
    prompt="your prompt",
    video_length_seconds=5,
    steps=6,  # 高速
    motion_strength=1.3,
    sage_attention=True
)
```

### ダイナミックな動き

```python
svi.generate_video(
    start_image_path="image.png",
    prompt="your prompt",
    video_length_seconds=5,
    steps=8,
    motion_strength=1.5,  # 強い動き
    sage_attention=True
)
```

---

## 実践的な使用例

### 例1: 基本的な動画生成

```python
from svi_wan22_video_integration import SVIWan22VideoIntegration

svi = SVIWan22VideoIntegration()

# 5秒の動画を生成
prompt_id = svi.generate_video(
    start_image_path="start.png",
    prompt="a peaceful Japanese garden with cherry blossoms",
    video_length_seconds=5,
    steps=6,
    motion_strength=1.3
)

print(f"生成開始: {prompt_id}")

# キュー状態を確認
queue = svi.get_queue_status()
print(f"キュー状態: {queue}")

# 履歴を確認
history = svi.get_history(max_items=5)
print(f"履歴: {len(history)}件")
```

### 例2: 無限生成（延長機能）

```python
# 最初の5秒を生成
prompt_id1 = svi.generate_video(
    start_image_path="start.png",
    prompt="a beautiful sunset",
    video_length_seconds=5,
    extend_enabled=True
)

# さらに5秒延長
prompt_id2 = svi.extend_video(
    previous_video_path="output/SVI_Wan22_00001.mp4",
    prompt="the sunset continues",
    extend_seconds=5
)

# さらに5秒延長（理論上無限に可能）
prompt_id3 = svi.extend_video(
    previous_video_path="output/SVI_Wan22_Extended_00001.mp4",
    prompt="the scene evolves",
    extend_seconds=5
)
```

### 例3: ストーリー性のある長編動画

```python
story_prompts = [
    {"timestamp": 0, "prompt": "a character with a smiling face"},
    {"timestamp": 5, "prompt": "the character becomes sad"},
    {"timestamp": 10, "prompt": "the character looks surprised"},
    {"timestamp": 15, "prompt": "the character is running"},
    {"timestamp": 20, "prompt": "the character reaches the destination"}
]

execution_ids = svi.create_story_video(
    start_image_path="character.png",
    story_prompts=story_prompts,
    segment_length_seconds=5,
    steps=6,
    motion_strength=1.3
)

print(f"{len(execution_ids)}個のセグメントを生成中...")
```

### 例4: タイムスタンプ付きプロンプト

```python
# 時間の経過とともにプロンプトを変更
timestamped_prompts = {
    "0": "morning scene, bright sunlight",
    "40": "noon scene, strong shadows",
    "80": "evening scene, golden hour",
    "120": "night scene, stars visible"
}

prompt_id = svi.generate_video(
    start_image_path="landscape.png",
    prompt="a landscape that changes throughout the day",
    video_length_seconds=15,
    timestamped_prompts=timestamped_prompts,
    steps=8,
    motion_strength=1.3
)
```

---

## トラブルシューティング

### ComfyUIが利用できない

```python
if not svi.is_available():
    print("ComfyUIが利用できません")
    print("確認事項:")
    print("1. ComfyUIサーバーが起動しているか")
    print("2. URLが正しいか（デフォルト: http://127.0.0.1:8188）")
    print("3. ネットワーク接続が正常か")
```

### エラーが発生する場合

1. **Sage Attentionエラー**: ローカル環境でエラーが出る場合は `sage_attention=False` に設定
2. **メモリ不足**: `steps` を減らすか、`sage_attention=True` を維持
3. **ワークフローノードが見つからない**: ComfyUIにSVI × Wan 2.2ワークフローがインストールされているか確認

### キュー状態の確認

```python
queue = svi.get_queue_status()
print(f"キュー状態: {queue}")

# 実行中/待機中のジョブ数を確認
if "queue_running" in queue:
    print(f"実行中: {len(queue['queue_running'])}件")
if "queue_pending" in queue:
    print(f"待機中: {len(queue['queue_pending'])}件")
```

---

## 高度な使い方

### カスタムワークフローテンプレート

ワークフローテンプレートファイル（`svi_wan22_workflow_template.json`）を作成することで、カスタムワークフローを使用できます。

### バッチ処理

```python
image_paths = ["image1.png", "image2.png", "image3.png"]
prompts = ["prompt1", "prompt2", "prompt3"]

execution_ids = []
for image_path, prompt in zip(image_paths, prompts):
    prompt_id = svi.generate_video(
        start_image_path=image_path,
        prompt=prompt,
        video_length_seconds=5
    )
    execution_ids.append(prompt_id)

print(f"{len(execution_ids)}個の動画を生成中...")
```

---

## APIリファレンス

### SVIWan22VideoIntegration クラス

#### メソッド

- `is_available() -> bool`: ComfyUIが利用可能かチェック
- `generate_video(...) -> Optional[str]`: 動画を生成
- `extend_video(...) -> Optional[str]`: 既存の動画を延長
- `create_story_video(...) -> List[Optional[str]]`: ストーリー性のある長編動画を作成
- `get_queue_status() -> Dict[str, Any]`: キュー状態を取得
- `get_history(max_items: int = 10) -> List[Dict[str, Any]]`: 実行履歴を取得
- `get_video(...) -> Optional[bytes]`: 生成された動画を取得

---

## 関連ドキュメント

- [SVI × Wan 2.2 AI動画生成技術 完全まとめ](../../Reports/SVI_Wan22_AI動画生成技術_完全まとめ.md)
- [ComfyUI統合ガイド](COMFYUI_SETUP.md)
- [ManaOS統合APIサーバー](unified_api_server.py)

---

## サポート

問題が発生した場合は、以下を確認してください:

1. ComfyUIサーバーのログ
2. ManaOS統合APIサーバーのログ
3. ワークフローノードのインストール状態
4. モデルファイルの存在

---

*最終更新: 2025-01-28*













