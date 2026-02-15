# SVI × Wan 2.2統合ガイド

## 概要

SVI × Wan 2.2統合により、ComfyUIを使用した無限長動画生成が可能になります。

## 機能

### 実装済み機能
- ✅ 基本的な動画生成
- ✅ 動画延長（既存動画の継続）
- ✅ ストーリー性のある長編動画生成
- ✅ キュー状態の取得
- ✅ 実行履歴の取得
- ✅ タイムスタンプ付きプロンプト対応

## APIエンドポイント

### 動画生成
```http
POST /api/svi/generate
Content-Type: application/json

{
  "start_image_path": "/path/to/image.png",
  "prompt": "beautiful landscape, cinematic",
  "video_length_seconds": 5,
  "steps": 6,
  "motion_strength": 1.3,
  "sage_attention": true,
  "extend_enabled": false,
  "timestamped_prompts": null
}
```

### 動画延長
```http
POST /api/svi/extend
Content-Type: application/json

{
  "previous_video_path": "/path/to/video.mp4",
  "prompt": "continue the scene",
  "extend_seconds": 5,
  "steps": 6,
  "motion_strength": 1.3
}
```

### ストーリー動画生成
```http
POST /api/svi/story
Content-Type: application/json

{
  "start_image_path": "/path/to/image.png",
  "story_prompts": [
    "sunrise over mountains",
    "birds flying in the sky",
    "sunset over ocean"
  ],
  "segment_length_seconds": 5,
  "steps": 6,
  "motion_strength": 1.3
}
```

### キュー状態取得
```http
GET /api/svi/queue
```

### 実行履歴取得
```http
GET /api/svi/history?max_items=10
```

## 使用例

### Pythonスクリプトから使用

#### シンプルな動画生成
```bash
python svi_example_simple_video.py
```

#### ストーリー動画生成
```bash
python svi_example_story_video.py
```

### REST APIから使用

```python
import requests

# 動画生成
response = requests.post("http://127.0.0.1:9510/api/svi/generate", json={
    "start_image_path": "/path/to/image.png",
    "prompt": "beautiful landscape",
    "video_length_seconds": 5
})

prompt_id = response.json()["prompt_id"]
print(f"生成開始: {prompt_id}")
```

## テスト

### 統合テストの実行
```bash
python test_svi_integration.py
```

テスト内容:
- モジュールの利用可能性確認
- APIサーバーのヘルスチェック
- 統合状態確認
- キュー・履歴取得テスト
- APIパラメータ確認

## パラメータ説明

### 動画生成パラメータ

- **start_image_path**: 開始画像のパス（必須）
- **prompt**: プロンプト（必須）
- **video_length_seconds**: 動画の長さ（秒、デフォルト: 5）
- **steps**: 生成ステップ数（デフォルト: 6）
- **motion_strength**: モーション強度（デフォルト: 1.3）
- **sage_attention**: Sage Attentionの使用（デフォルト: true）
- **extend_enabled**: 延長機能の有効化（デフォルト: false）
- **timestamped_prompts**: タイムスタンプ付きプロンプト（オプション）

### 動画延長パラメータ

- **previous_video_path**: 前の動画のパス（必須）
- **prompt**: 延長プロンプト（必須）
- **extend_seconds**: 延長秒数（デフォルト: 5）
- **steps**: 生成ステップ数（デフォルト: 6）
- **motion_strength**: モーション強度（デフォルト: 1.3）

### ストーリー動画生成パラメータ

- **start_image_path**: 開始画像のパス（必須）
- **story_prompts**: ストーリープロンプトのリスト（必須）
- **segment_length_seconds**: 各セグメントの長さ（秒、デフォルト: 5）
- **steps**: 生成ステップ数（デフォルト: 6）
- **motion_strength**: モーション強度（デフォルト: 1.3）

## トラブルシューティング

### ComfyUIが利用できない

```bash
# ComfyUIサーバーが起動しているか確認
curl http://127.0.0.1:8188/system_stats

# ComfyUIを起動
cd C:\ComfyUI
python main.py --port 8188
```

### カスタムノードが見つからない

1. ComfyUI Managerで「Install Missing Custom Nodes」を実行
2. 必要なカスタムノードを手動でインストール:
   - ComfyUI-VideoHelperSuite
   - ComfyUI-AnimateDiff-Evolved
   - ComfyUI-Stable-Video-Diffusion

### モデルファイルが見つからない

Wan 2.2モデルを以下のパスに配置:
```
C:\ComfyUI\models\checkpoints\wan2.2.safetensors
```

## 関連ドキュメント

- [セットアップ完了ガイド](./SVI_WAN22_SETUP_COMPLETE.md)
- [ComfyUIセットアップガイド](./COMFYUI_SETUP.md)

## ファイル一覧

```
manaos_integrations/
├── svi_wan22_video_integration.py    # メインモジュール
├── test_svi_integration.py           # テストスクリプト
├── svi_example_simple_video.py       # シンプルな動画生成の実例
├── svi_example_story_video.py        # ストーリー動画生成の実例
├── SVI_WAN22_SETUP_COMPLETE.md       # セットアップ完了ガイド
└── SVI_INTEGRATION_GUIDE.md          # このガイド
```












