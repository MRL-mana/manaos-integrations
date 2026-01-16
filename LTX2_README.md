# LTX-2動画生成統合（Super LTX-2設定）

LTX-2動画生成モデルをManaOS統合システムに統合したモジュールです。記事「Super LTX-2 セッティング」を参考に、推奨設定を実装しています。

## 特徴

- ✅ **NAG (Negative Attention Guidance)**: 品質を劇的に安定させる技術
- ✅ **res_2sサンプラー**: 破綻を防ぎ滑らかな動きを実現
- ✅ **2段階生成（アップスケール）**: 効率とクオリティの両立
- ✅ **Q8 GGUFモデル**: 推奨モデル（品質とパフォーマンスのバランス）
- ✅ **日本語プロンプト対応**: 自動的に英語に翻訳

## 必要な環境

- ComfyUI（統合済み）
- Python 3.8以上
- VRAM 8GB〜（Q8 GGUFモデル推奨）

## クイックスタート

### 1. セットアップ

```powershell
# セットアップスクリプトを実行
.\setup_ltx2.ps1
```

または、カスタムノードのみインストールする場合：

```powershell
# カスタムノードをインストール
python install_ltx2_custom_nodes.py
```

### 2. モデルの準備

LTX-2 Q8 GGUFモデルをダウンロードして配置：

- **ダウンロード先**: https://huggingface.co/unsloth/LTX-2-GGUF
- **配置場所**: `ComfyUI/models/unet/`
- **モデルサイズ**: 約43GB
- **VRAM要件**: 8GB〜

### 3. 動作確認

```powershell
# テストスクリプトを実行
python test_ltx2.py
```

## 必要なカスタムノード

以下のカスタムノードが必要です（自動インストールスクリプトでインストール可能）：

1. **ComfyUI-KJNodes**（必須）
   - NAG機能を使用するために必要
   - GitHub: https://github.com/kijai/ComfyUI-KJNodes

2. **ComfyUI-GGUF**（必須）
   - GGUFモデル（Q8 GGUFなど）をサポート
   - GitHub: https://github.com/city96/ComfyUI-GGUF

3. **ComfyUI-VideoHelperSuite**（推奨）
   - 動画処理ユーティリティ
   - GitHub: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite

## 使用方法

### API経由で使用

```python
import requests

# 動画生成
response = requests.post("http://localhost:5000/api/ltx2/generate", json={
    "start_image_path": "path/to/image.png",
    "prompt": "a beautiful landscape, mountains, sunset",
    "negative_prompt": "blurry, low quality",
    "video_length_seconds": 5,
    "width": 512,
    "height": 512,
    "use_two_pass": True,  # 2段階生成を使用（推奨）
    "use_nag": True,  # NAGを使用（推奨）
    "use_res2s_sampler": True,  # res_2sサンプラーを使用（推奨）
    "model_name": "ltx2-q8.gguf"
})

result = response.json()
prompt_id = result["prompt_id"]

# 状態確認
status_response = requests.get(f"http://localhost:5000/api/ltx2/status/{prompt_id}")
status = status_response.json()
print(status)
```

### Pythonモジュールとして使用

```python
from ltx2_video_integration import LTX2VideoIntegration

# 統合を初期化
ltx2 = LTX2VideoIntegration()

# 動画生成
prompt_id = ltx2.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    negative_prompt="blurry, low quality",
    video_length_seconds=5,
    use_two_pass=True,  # 推奨: 2段階生成
    use_nag=True,  # 推奨: NAG使用
    use_res2s_sampler=True,  # 推奨: res_2sサンプラー
    model_name="ltx2-q8.gguf"
)

if prompt_id:
    print(f"動画生成を開始しました: {prompt_id}")
    
    # キュー状態を確認
    queue_status = ltx2.get_queue_status()
    print(f"キュー状態: {queue_status}")
    
    # 履歴を確認
    history = ltx2.get_history(max_items=10)
    print(f"実行履歴: {history}")
```

## APIエンドポイント

### `POST /api/ltx2/generate`

動画生成を開始します。

**リクエストボディ:**
```json
{
  "start_image_path": "path/to/image.png",
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "video_length_seconds": 5,
  "width": 512,
  "height": 512,
  "use_two_pass": true,
  "use_nag": true,
  "use_res2s_sampler": true,
  "model_name": "ltx2-q8.gguf"
}
```

**レスポンス:**
```json
{
  "prompt_id": "生成された実行ID",
  "status": "success",
  "message": "動画生成が開始されました（Super LTX-2設定）"
}
```

### `GET /api/ltx2/queue`

キュー状態を取得します。

### `GET /api/ltx2/history?max_items=10`

実行履歴を取得します。

### `GET /api/ltx2/status/<prompt_id>`

特定の実行IDの状態を取得します。

## 推奨設定

記事「Super LTX-2 セッティング」の推奨設定：

- **use_two_pass**: `true`（2段階生成を使用）
- **use_nag**: `true`（NAGを使用）
- **use_res2s_sampler**: `true`（res_2sサンプラーを使用）
- **model_name**: `"ltx2-q8.gguf"`（Q8 GGUFモデル）

## トラブルシューティング

### ComfyUIに接続できない

1. ComfyUIが起動しているか確認: http://localhost:8188
2. ComfyUIのポートが8188であることを確認
3. ファイアウォールの設定を確認

### カスタムノードが見つからない

1. カスタムノードがインストールされているか確認
2. ComfyUIを再起動（カスタムノードを読み込むため）
3. 手動でインストール: `python install_ltx2_custom_nodes.py`

### モデルが見つからない

1. LTX-2モデルが`ComfyUI/models/unet/`に配置されているか確認
2. モデルファイル名が正しいか確認（`ltx2-q8.gguf`など）
3. モデルファイルが破損していないか確認

### 動画生成が失敗する

1. VRAMが不足していないか確認（8GB〜推奨）
2. ComfyUIのログを確認
3. ワークフローが正しく設定されているか確認

## 参考資料

- **参考記事**: https://note.com/ai_hakase/n/n01d2855d90cd
- **統合計画書**: `LTX2_INTEGRATION_PLAN.md`
- **クイックスタートガイド**: `ltx2_quick_start_guide.md`
- **使用例集**: `LTX2_USAGE_EXAMPLES.md`
- **セットアップ完了報告**: `LTX2_SETUP_COMPLETE.md`
- **テストスクリプト**: `test_ltx2.py`
- **セットアップスクリプト**: `setup_ltx2.ps1`

## ファイル構成

```
manaos_integrations/
├── ltx2_video_integration.py          # LTX-2統合モジュール
├── install_ltx2_custom_nodes.py       # カスタムノードインストールスクリプト
├── setup_ltx2.ps1                     # セットアップスクリプト
├── test_ltx2.py                       # テストスクリプト
├── ltx2_example_simple_video.py       # シンプルな動画生成の実用例
├── ltx2_batch_example.py              # バッチ動画生成の実用例
├── ltx2_workflow_template.json        # ワークフローテンプレート（参考用）
├── LTX2_README.md                     # このファイル（詳細な使用方法）
├── LTX2_INTEGRATION_PLAN.md           # 統合計画書
├── LTX2_SETUP_COMPLETE.md             # セットアップ完了報告
├── LTX2_USAGE_EXAMPLES.md             # 使用例集
├── ltx2_quick_start_guide.md          # クイックスタートガイド
└── unified_api_server.py              # API統合（LTX-2エンドポイント追加済み）
```

## ライセンス

この統合モジュールはManaOS統合システムの一部です。
