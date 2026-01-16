# LTX-2統合計画

## 概要
記事「Super LTX-2 セッティング」を参考に、LTX-2動画生成モデルをManaOS統合システムに追加する計画。

## 記事の要点
- **NAG (Negative Attention Guidance)**: 品質を劇的に安定させる技術
- **res_2sサンプラー**: 破綻を防ぎ滑らかな動きを実現
- **2段階生成（アップスケール）**: 効率とクオリティの両立
- **Q8 GGUFモデル**: 推奨モデル（品質とパフォーマンスのバランス）

## 現在の状況
- ✅ ComfyUIは統合済み
- ✅ SVI × Wan 2.2動画生成統合の実装パターンが存在
- ❌ LTX-2は未統合

## 必要な作業

### 1. モデルの準備
- LTX-2 Q8 GGUFモデルのダウンロード
- モデルファイルの配置（ComfyUIモデルディレクトリ）

### 2. カスタムノードのインストール
- **KJNodes**: NAG機能を使用するために必要
  - GitHub: https://github.com/kijai/ComfyUI-KJNodes
  - 最新バージョンが必要

### 3. ワークフローの実装
- 2段階生成（アップスケール）ワークフローの作成
- res_2sサンプラーの設定
- NAG設定の組み込み

### 4. 統合コードの作成
- `ltx2_video_integration.py`の作成
- `unified_api_server.py`への統合
- APIエンドポイントの追加

## 参考記事
- https://note.com/ai_hakase/n/n01d2855d90cd

## 注意事項
- VRAM要件: Q8 GGUFモデルを使用する場合、VRAM 8GB〜推奨
- モデルサイズ: Q8 GGUFモデルは約43GB（圧縮後でも大きい）
- カスタムノード: KJNodesの最新バージョンが必要（NAG機能のため）

## 実装状況

### ✅ 完了した実装

1. **LTX-2統合モジュール** (`ltx2_video_integration.py`)
   - ✅ NAG (Negative Attention Guidance) 対応
   - ✅ res_2sサンプラー対応
   - ✅ 2段階生成（アップスケール）ワークフロー対応
   - ✅ Q8 GGUFモデル対応
   - ✅ 日本語プロンプトの英語翻訳機能

2. **カスタムノードインストールスクリプト** (`install_ltx2_custom_nodes.py`)
   - ✅ KJNodes自動インストール
   - ✅ ComfyUI-GGUF自動インストール
   - ✅ 依存関係の自動インストール

3. **セットアップスクリプト** (`setup_ltx2.ps1`)
   - ✅ ComfyUIパスの自動検出
   - ✅ カスタムノードの自動インストール
   - ✅ ワークフローテンプレートの配置
   - ✅ モデルファイルの確認

4. **API統合** (`unified_api_server.py`)
   - ✅ LTX-2統合モジュールのインポート
   - ✅ 統合システムへの追加
   - ✅ APIエンドポイントの追加:
     - `POST /api/ltx2/generate` - 動画生成
     - `GET /api/ltx2/queue` - キュー状態取得
     - `GET /api/ltx2/history` - 実行履歴取得
     - `GET /api/ltx2/status/<prompt_id>` - 実行状態取得

### 📝 次のステップ

1. **モデルの準備**
   - LTX-2 Q8 GGUFモデルをダウンロード
   - ダウンロード先: https://huggingface.co/unsloth/LTX-2-GGUF
   - 配置場所: `ComfyUI/models/unet/`

2. **セットアップの実行**
   ```powershell
   .\setup_ltx2.ps1
   ```

3. **動作確認**
   - ComfyUIを再起動（カスタムノードを読み込むため）
   - APIエンドポイントで動作確認

## 使用方法

### セットアップ
```powershell
# セットアップスクリプトを実行
.\setup_ltx2.ps1

# カスタムノードのみインストールする場合
python install_ltx2_custom_nodes.py
```

### API使用例
```python
import requests

# 動画生成
response = requests.post("http://localhost:5000/api/ltx2/generate", json={
    "start_image_path": "path/to/image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "negative_prompt": "blurry, low quality",
    "video_length_seconds": 5,
    "use_two_pass": True,
    "use_nag": True,
    "use_res2s_sampler": True,
    "model_name": "ltx2-q8.gguf"
})

result = response.json()
prompt_id = result["prompt_id"]

# 状態確認
status_response = requests.get(f"http://localhost:5000/api/ltx2/status/{prompt_id}")
status = status_response.json()
```

### 統合モジュール使用例
```python
from ltx2_video_integration import LTX2VideoIntegration

ltx2 = LTX2VideoIntegration()
prompt_id = ltx2.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    use_two_pass=True,
    use_nag=True,
    use_res2s_sampler=True
)
```

## クイックスタートガイド

### 1. セットアップ

```powershell
# セットアップスクリプトを実行
.\setup_ltx2.ps1
```

これにより以下が実行されます：
- ComfyUIパスの自動検出
- カスタムノードの自動インストール（KJNodes、ComfyUI-GGUFなど）
- ワークフローテンプレートの配置
- モデルファイルの確認

### 2. モデルの準備

LTX-2 Q8 GGUFモデルをダウンロード：

- **ダウンロード先**: https://huggingface.co/unsloth/LTX-2-GGUF
- **配置場所**: `ComfyUI/models/unet/`
- **モデルサイズ**: 約43GB
- **VRAM要件**: 8GB〜

### 3. ComfyUIの再起動

カスタムノードを読み込むためにComfyUIを再起動してください。

### 4. 動作確認

```powershell
# テストスクリプトを実行
python test_ltx2.py
```

### 5. 使用開始

#### API経由

```python
import requests

response = requests.post("http://localhost:5000/api/ltx2/generate", json={
    "start_image_path": "image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "use_two_pass": True,
    "use_nag": True,
    "use_res2s_sampler": True
})
```

#### Pythonモジュール

```python
from ltx2_video_integration import LTX2VideoIntegration

ltx2 = LTX2VideoIntegration()
prompt_id = ltx2.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    use_two_pass=True,
    use_nag=True,
    use_res2s_sampler=True
)
```

## 詳細ドキュメント

- **README**: `LTX2_README.md` - 詳細な使用方法とトラブルシューティング
- **クイックスタートガイド**: `ltx2_quick_start_guide.md` - クイックスタートガイド
- **使用例集**: `LTX2_USAGE_EXAMPLES.md` - 実用的な使用例集
- **テストスクリプト**: `test_ltx2.py` - 動作確認用スクリプト
- **セットアップ完了報告**: `LTX2_SETUP_COMPLETE.md` - セットアップ完了報告

## 実用的な使用例スクリプト

1. **ltx2_example_simple_video.py** - シンプルな動画生成の実用例
2. **ltx2_batch_example.py** - バッチ動画生成の実用例

## 実装ファイル一覧

- `ltx2_video_integration.py` - LTX-2統合モジュール
- `install_ltx2_custom_nodes.py` - カスタムノードインストールスクリプト
- `setup_ltx2.ps1` - セットアップスクリプト
- `test_ltx2.py` - テストスクリプト
- `ltx2_example_simple_video.py` - シンプルな動画生成の実用例
- `ltx2_batch_example.py` - バッチ動画生成の実用例
- `ltx2_workflow_template.json` - ワークフローテンプレート（参考用）
- `unified_api_server.py` - API統合（LTX-2エンドポイント追加済み）
