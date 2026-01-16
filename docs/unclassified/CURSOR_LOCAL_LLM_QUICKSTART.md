# 🚀 Cursor × ローカルLLM クイックスタート

**マナ仕様：最短5分で接続成功**

---

## ⚡ 最短手順（LM Studio編）

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
   - 「こんにちは！接続できていますか？」と入力

2. **応答が返ってくれば成功！** ✅

---

## 📋 チェックリスト

- [ ] LM Studioをインストール
- [ ] モデルをダウンロード（Qwen2.5-Coder-7B-Instruct）
- [ ] サーバーを起動（`http://localhost:1234/v1`）
- [ ] CursorにカスタムLLMを登録
- [ ] Cursorを再起動
- [ ] チャットで接続テスト

---

## 🎯 次のステップ

接続成功したら、以下を実装：

1. ✅ **モデル最適化**（`CURSOR_MODEL_RECOMMENDATIONS.md`）
2. ✅ **運用ルール確立**（`CURSOR_PROMPT_TEMPLATES.md`）
3. ✅ **ManaOS統合**（`MANAOS_LLM_ROUTING.md`）

---

## 🔗 関連ドキュメント

- `CURSOR_LOCAL_LLM_SETUP.md` - 詳細な接続設定手順
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `MANAOS_LLM_ROUTING.md` - ManaOS統合設計

---

## 🚨 トラブルシューティング

### 接続できない場合

1. **LM Studioのサーバーが起動しているか確認**
   - 「Server」タブで「Server is running」が表示されているか

2. **Base URLを確認**
   - `http://localhost:1234/v1` の `/v1` が付いているか

3. **Firewallを確認**
   - Windows Firewallで `localhost:1234` が許可されているか

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

**これで接続成功！次は運用ルールを詰めよう🔥**



















