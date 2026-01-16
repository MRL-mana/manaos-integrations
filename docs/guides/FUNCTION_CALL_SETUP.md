# 🔧 関数呼び出し（Function Call）設定ガイド

**作成日**: 2025-01-10

---

## ✅ 現在の状態

- ✅ OpenAPI仕様: 正常に動作中（`/openapi.json`）
- ✅ 「関数呼び出し」パラメータ: 有効（「大丈夫」と表示）
- ⚠️ 外部ツールの設定が必要

---

## 📋 設定手順

### ステップ1: External ToolsでmanaOS統合APIを追加

1. 設定画面（右上の⚙️）を開く
2. 「**External Tools**」タブを選択
3. 「**接続を追加**」ボタンをクリック
4. 以下の情報を入力：

   - **URL**: `http://host.docker.internal:9500`
   - **OpenAPI Spec**: **ON**（緑）にする
   - OpenAPI Spec URL: `openapi.json`
   - **認証**: 空白でOK

5. 「**保存**」をクリック

### ステップ2: 「機能」ドロップダウンで関数を選択

設定が完了すると、「**機能**」ドロップダウンに以下の関数が表示されます：

- **generateImageComfyUI** - ComfyUIで画像を生成
- **uploadToGoogleDrive** - Google Driveにファイルをアップロード
- **createObsidianNote** - Obsidianにノートを作成
- **searchCivitAIModels** - CivitAIでモデルを検索

### ステップ3: チャットで使用

1. チャット画面に戻る
2. モデルを選択（LM StudioまたはOllama）
3. 「ComfyUIで画像を生成して、美しい風景を描いて」などと入力
4. LLMが自動的にmanaOS統合APIの関数を呼び出します

---

## 🎯 使い方

### 手動で関数を選択する場合

1. チャットコントロール画面で「**機能**」ドロップダウンを開く
2. 使用したい関数を選択（例：`generateImageComfyUI`）
3. チャットでプロンプトを入力

### 自動で関数を呼び出す場合

1. チャット画面で自然なメッセージを入力（例：「画像を生成して」）
2. LLMが自動的に適切な関数を選択して呼び出す

---

## ✅ 確認事項

- ✅ OpenAPI仕様: `/openapi.json` が正常に返ってくる
- ✅ 関数呼び出し: パラメータが「大丈夫」と表示されている
- ⚠️ External Tools: 設定が完了しているか確認

---

**External ToolsでmanaOS統合APIを追加すれば、すぐに使えます！**
