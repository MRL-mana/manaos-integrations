# 🚀 Cursor × ローカルLLM クイックスタートガイド

**最短5分で接続成功まで到達**

---

## ⚡ 自動セットアップ（推奨）

### ステップ1：自動セットアップスクリプトを実行

```powershell
.\setup_cursor_local_llm.ps1
```

このスクリプトが以下を自動実行：
- LM Studioサーバーの確認
- Cursor設定ファイルの確認・更新
- 設定ファイルの生成
- 依存関係の確認・インストール

---

## 📋 手動セットアップ

### ステップ1：LM Studioを起動（2分）

1. **LM Studioをダウンロード**
   - https://lmstudio.ai/ からWindows版をダウンロード
   - インストール

2. **モデルをダウンロード**
   - 「Search」タブで `Qwen2.5-Coder-7B-Instruct` を検索
   - ダウンロード（Q4量子化推奨）

3. **サーバーを起動**
   - 「Server」タブでモデルを選択
   - 「Start Server」をクリック
   - エンドポイント確認：`http://localhost:1234/v1`

---

### ステップ2：Cursorに登録（2分）

1. **Cursorの設定を開く**
   - `Ctrl + ,` で設定を開く

2. **カスタムLLMを追加**
   - 「Add Custom Model」をクリック
   - 以下を入力：
     - **Provider**: `OpenAI Compatible`
     - **Base URL**: `http://localhost:1234/v1`
     - **API Key**: `lm-studio`
     - **Model Name**: `Qwen2.5-Coder-7B-Instruct`

3. **Cursorを再起動**

---

### ステップ3：接続テスト（1分）

1. **チャットを開く**
   - `Ctrl + L` でチャットを開く
   - 簡単な質問を入力：
     ```
     こんにちは！接続できていますか？
     ```
2. **応答が返ってくれば成功！** ✅

---

## 🔍 状態確認

### セットアップ状態をチェック

```powershell
.\check_llm_setup.ps1
```

このスクリプトが以下を確認：
- LM Studioサーバーの状態
- Ollamaサーバーの状態（オプション）
- 拡張LLMルーティングAPIの状態
- 統合APIサーバーの状態（オプション）
- 設定ファイルの存在
- Pythonモジュールのインストール状況
- 実装ファイルの存在

---

## 🧪 テスト実行

### 統合テスト

```powershell
python test_llm_routing.py
```

### 使用例の実行

```powershell
python example_usage.py
```

---

## 📊 API使用例

### Pythonから使用

```python
import requests

# 難易度分析
response = requests.post(
    "http://localhost:9500/api/llm/analyze",
    json={
        "prompt": "この関数のタイポを修正して",
        "context": {
            "code_context": "def hello():\n    print('helo')"
        }
    }
)
print(response.json())

# ルーティング実行
response = requests.post(
    "http://localhost:9500/api/llm/route-enhanced",
    json={
        "prompt": "この関数のタイポを修正して",
        "context": {
            "code_context": "def hello():\n    print('helo')"
        },
        "preferences": {
            "prefer_speed": True
        }
    }
)
print(response.json())
```

---

## 🚨 トラブルシューティング

### 接続できない場合

1. **LM Studioのサーバーが起動しているか確認**
   ```powershell
   .\check_llm_setup.ps1
   ```

2. **Firewallを確認**
   - Windows Firewallで `localhost:1234` が許可されているか

3. **Cursorを再起動**
   - 設定変更後は再起動が必要

### 遅い場合

1. **モデルサイズを確認**
   - 7Bモデルを使用しているか（32Bは重い）

2. **量子化レベルを確認**
   - Q4量子化を使用しているか（FP16は重い）

### 応答が薄い場合

1. **モデルを確認**
   - Coder系モデルを使用しているか（汎用モデルはコード弱い）

2. **プロンプトを確認**
   - プロンプトテンプレートを使用しているか

---

## 📝 次のステップ

接続成功したら、以下を実装：

1. ✅ **モデル最適化**（`CURSOR_MODEL_RECOMMENDATIONS.md`）
2. ✅ **運用ルール確立**（`CURSOR_PROMPT_TEMPLATES.md`）
3. ✅ **ManaOS統合**（`MANAOS_LLM_ROUTING.md`）

---

## 🔗 関連ドキュメント

- `CURSOR_LOCAL_LLM_SETUP.md` - 詳細な接続設定手順
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `LLM_ROUTING_README.md` - API使い方ガイド

---

**これで接続成功まで到達！次は運用ルールを詰めよう🔥**



















