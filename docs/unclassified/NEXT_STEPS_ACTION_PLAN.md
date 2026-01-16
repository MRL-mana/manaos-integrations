# 🔥 次のステップ - アクションプラン

## 📋 現在の状況

### ✅ 完了済み

1. **Tool Serverの実装完了**
   - FastAPIベースのTool Server実装
   - 3つのツール実装（service_status, check_errors, generate_image）

2. **エンドポイントパスの修正**
   - 公式参考実装と同じ構造に修正済み
   - `/api/tools/service_status` → `/service_status`
   - `/api/tools/check_errors` → `/check_errors`
   - `/api/tools/generate_image` → `/generate_image`

3. **Tool Serverの起動確認**
   - Tool Serverは正常に起動中（http://localhost:9503）
   - OpenAPI仕様も正常に取得可能

4. **公式参考実装の確認**
   - `open-webui/openapi-servers`リポジトリを確認
   - エンドポイントパス構造が一致していることを確認

### ⏳ 次のステップ

1. **OpenWebUIの「外部ツール」設定画面でTool Serverを登録**
2. **接続状態を確認**
3. **「関数呼び出し」の設定を確認**
4. **ツールの表示確認**

---

## 🎯 アクションプラン

### Step 1: Tool Serverの状態を確認 ✅

```powershell
# Tool Serverのヘルスチェック
curl http://localhost:9503/health

# OpenAPI仕様の確認
curl http://localhost:9503/openapi.json
```

### Step 2: OpenWebUIの「外部ツール」設定画面でTool Serverを登録

1. **OpenWebUIにアクセス**
   - http://localhost:3001 にアクセス

2. **「外部ツール」設定画面を開く**
   - 左サイドバーの「設定」→「外部ツール」をクリック
   - または、URLから直接: http://localhost:3001/admin/settings/external-tools

3. **「接続を追加」をクリック**

4. **以下の情報を入力**
   - **URL (APIベースURL)**: `http://localhost:9503`
   - **OpenAPI仕様URL**: `openapi.json`
   - **認証 (Authentication)**: 「なし (None)」または「パブリック (Public)」
   - **名前 (Name)**: `manaOS Tool Server`
   - **説明 (Description)**: `Docker/service status, log check, ComfyUI image generation`（任意）

5. **「保存」をクリック**

### Step 3: 接続状態を確認

1. **Tool Serverの接続状態を確認**
   - 「Connected」になっているか確認
   - 「Disconnected」または「Error」の場合、接続を再試行

2. **エラーメッセージがないか確認**
   - エラーがある場合、エラーメッセージを確認

### Step 4: 「関数呼び出し」の設定を確認

1. **チャット画面に戻る**
   - 設定画面を閉じて、チャット画面に戻る

2. **「チャットコントロール」を開く**
   - チャット画面で「チャットコントロール」を開く

3. **「高なパラメータ」セクションを展開**
   - 「高なパラメータ」セクションを展開

4. **「関数呼び出し」をクリック**
   - 「関数呼び出し (Function Calling)」をクリック

5. **「有効 (Enabled)」または「自動 (Auto)」を選択**
   - 「有効 (Enabled)」または「自動 (Auto)」を選択

### Step 5: ツールの表示確認

1. **「ツールの選択」ドロップダウンを確認**
   - 「バルブ」セクションの「ツールの選択」ドロップダウンを確認
   - Tool Serverのツール（service_status, check_errors, generate_image）が表示されることを確認

2. **ツールが表示されない場合**
   - ブラウザのキャッシュをクリア（F5またはCtrl + F5）
   - OpenWebUIを再起動
   - Tool Serverを再起動

---

## 🔥 レミ先輩の推奨

### 優先度1: Tool Serverの登録

1. **OpenWebUIの「外部ツール」設定画面でTool Serverを登録**
   - これが最重要
   - 登録後、接続状態を確認

### 優先度2: 設定の確認

1. **「関数呼び出し」の設定を確認**
   - 「有効 (Enabled)」または「自動 (Auto)」に設定

2. **接続状態を確認**
   - 「Connected」になっているか確認

### 優先度3: 動作確認

1. **ツールの表示確認**
   - 「ツールの選択」ドロップダウンで確認

2. **動作テスト**
   - チャットで「dockerコンテナの状態を確認して」と送信
   - LLMが`service_status`ツールを呼び出すことを確認

---

## 📋 確認チェックリスト

- [ ] Tool Serverが起動中（http://localhost:9503/health）
- [ ] OpenAPI仕様が取得できる（http://localhost:9503/openapi.json）
- [ ] OpenWebUIの「外部ツール」設定画面でTool Serverを登録
- [ ] Tool Serverの接続状態が「Connected」
- [ ] 「関数呼び出し」が「有効 (Enabled)」または「自動 (Auto)」に設定
- [ ] 「ツールの選択」ドロップダウンでツールが表示される
- [ ] チャットでツールの動作確認

---

**レミ先輩モード**: どんどん進めよう！まずはOpenWebUIの「外部ツール」設定画面でTool Serverを登録することが最重要！🔥
