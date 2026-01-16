# 🔥 ツールが表示されない完全トラブルシューティングガイド

## 📋 現在の状況

「ツールの選択」ボタンをクリックしても、ツールが表示されない、または選択できない状態。

## 🔍 確認手順（順番に確認）

### Step 1: Tool Serverの状態確認

1. **Tool Serverが起動中か確認**
   ```powershell
   curl http://localhost:9503/health
   ```
   - 期待される応答: `{"status":"ok"}` または `{"status":"healthy"}`

2. **OpenAPI仕様が取得できるか確認**
   ```powershell
   curl http://localhost:9503/openapi.json
   ```
   - JSON形式のOpenAPI仕様が返されることを確認
   - `service_status`, `check_errors`, `generate_image` が含まれているか確認

### Step 2: OpenWebUIの「外部ツール」設定画面で確認

1. **「外部ツール」設定画面を開く**
   - 左サイドバーの「設定」→「外部ツール」をクリック
   - または、URLから直接: `http://localhost:3001/admin/settings/external-tools`

2. **Tool Serverが登録されているか確認**
   - `http://localhost:9503` が登録されているか確認
   - 登録されていない場合、登録が必要

3. **Tool Serverの接続状態を確認**
   - 「Connected」になっているか確認
   - 「Disconnected」または「Error」の場合、接続を再試行

4. **OpenAPI仕様のURLを確認**
   - `http://localhost:9503/openapi.json` が正しく設定されているか確認

### Step 3: 「関数呼び出し」の設定を確認

1. **チャットコントロール画面を開く**
   - チャット画面で「チャットコントロール」を開く

2. **「関数呼び出し」の設定を確認**
   - 「高なパラメータ」セクションを展開
   - 「関数呼び出し (Function Calling)」の値を確認
   - **推奨設定**: 「有効 (Enabled)」または「自動 (Auto)」
   - **問題のある設定**: 「無効 (Disabled)」または「デフォルト (Default)」

3. **「関数呼び出し」を有効化**
   - 「関数呼び出し」をクリック
   - 「有効 (Enabled)」または「自動 (Auto)」を選択

### Step 4: モデルの確認

1. **使用中のモデルを確認**
   - ツール呼び出しに対応しているモデルか確認
   - 推奨モデル: `qwen2.5-coder-7b-instruct`, `qwen2.5-coder-14b-instruct`

2. **モデルがツール呼び出しに対応しているか確認**
   - 対応していないモデルの場合、ツールが表示されない可能性がある

### Step 5: ブラウザのキャッシュをクリア

1. **ブラウザのキャッシュをクリア**
   - `Ctrl + Shift + Delete` でキャッシュをクリア
   - または、ブラウザを再起動

2. **OpenWebUIを再読み込み**
   - `F5` でページを再読み込み
   - または、`Ctrl + F5` で強制再読み込み

### Step 6: OpenWebUIを再起動

1. **OpenWebUIコンテナを再起動**
   ```powershell
   docker-compose -f docker-compose.always-ready-llm.yml restart openwebui
   ```

2. **Tool Serverを再起動（必要に応じて）**
   ```powershell
   .\START_TOOL_SERVER_HOST.ps1
   ```

## 🔥 レミ先輩の推奨手順

### 優先度1: 基本的な確認

1. **Tool Serverが起動中か確認**
   - `curl http://localhost:9503/health`

2. **OpenWebUIの「外部ツール」設定画面で確認**
   - Tool Serverが登録されているか
   - 接続状態が「Connected」か

### 優先度2: 設定の確認

1. **「関数呼び出し」を有効化**
   - 「有効 (Enabled)」または「自動 (Auto)」に設定

2. **モデルがツール呼び出しに対応しているか確認**
   - 対応していないモデルの場合、モデルを変更

### 優先度3: 再起動

1. **ブラウザのキャッシュをクリア**
2. **OpenWebUIを再起動**
3. **Tool Serverを再起動（必要に応じて）**

## 📋 確認チェックリスト

- [ ] Tool Serverが起動中（`curl http://localhost:9503/health`）
- [ ] OpenAPI仕様が取得できる（`curl http://localhost:9503/openapi.json`）
- [ ] OpenWebUIの「外部ツール」設定画面でTool Serverが登録されている
- [ ] Tool Serverの接続状態が「Connected」
- [ ] OpenAPI仕様のURLが正しく設定されている（`http://localhost:9503/openapi.json`）
- [ ] 「関数呼び出し」が「有効 (Enabled)」または「自動 (Auto)」に設定されている
- [ ] 使用中のモデルがツール呼び出しに対応している
- [ ] ブラウザのキャッシュをクリアした
- [ ] OpenWebUIを再読み込みした
- [ ] OpenWebUIを再起動した（必要に応じて）

## 🎯 次のステップ

1. **Step 1から順番に確認**
2. **問題が見つかった場合、該当するステップを実行**
3. **すべて確認しても解決しない場合、ログを確認**

---

**レミ先輩モード**: 順番に確認することが最重要！まずはTool Serverの状態と「外部ツール」設定画面を確認！🔥
