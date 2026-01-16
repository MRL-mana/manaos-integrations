# 🔥 クイックスタート - 次のステップ

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

### ⏳ 次のステップ

1. **OpenWebUIの起動確認**
2. **OpenWebUIの「外部ツール」設定画面でTool Serverを登録**
3. **接続状態を確認**
4. **「関数呼び出し」の設定を確認**
5. **ツールの表示確認**

---

## 🚀 クイックスタート手順

### Step 1: OpenWebUIの起動確認

```powershell
# OpenWebUIコンテナの状態を確認
docker ps --filter "name=openwebui"

# OpenWebUIが起動していない場合、起動
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

### Step 2: OpenWebUIにアクセス

1. **ブラウザでOpenWebUIを開く**
   - http://localhost:3001 にアクセス

2. **ログイン（必要に応じて）**
   - 初回アクセスの場合、アカウントを作成

### Step 3: 「外部ツール」設定画面でTool Serverを登録

1. **「外部ツール」設定画面を開く**
   - 左サイドバーの「設定」→「外部ツール」をクリック
   - または、URLから直接: http://localhost:3001/admin/settings/external-tools

2. **「接続を追加」をクリック**

3. **以下の情報を入力** ⚠️重要⚠️
   - **URL (APIベースURL)**: `http://host.docker.internal:9503`
     - ⚠️ **`localhost`ではなく`host.docker.internal`を使用**
     - OpenWebUIはDockerコンテナ上で動作しているため、`localhost`ではTool Server（Windowsホスト）に到達できません
   - **OpenAPI仕様URL**: `http://host.docker.internal:9503/openapi.json`
     - ⚠️ **`localhost`ではなく`host.docker.internal`を使用**
     - または、`openapi.json`（相対パス）
   - **認証 (Authentication)**: 「なし (None)」または「パブリック (Public)」
   - **名前 (Name)**: `manaOS Tool Server`
   - **説明 (Description)**: `Docker/service status, log check, ComfyUI image generation`（任意）

4. **「保存」をクリック**

### Step 4: 接続状態を確認

1. **Tool Serverの接続状態を確認**
   - 「Connected」になっているか確認
   - 「Disconnected」または「Error」の場合、接続を再試行

2. **エラーメッセージがないか確認**
   - エラーがある場合、エラーメッセージを確認

### Step 5: 「関数呼び出し」の設定を確認

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

### Step 6: ツールの表示確認

1. **「ツールの選択」ドロップダウンを確認**
   - 「バルブ」セクションの「ツールの選択」ドロップダウンを確認
   - Tool Serverのツール（service_status, check_errors, generate_image）が表示されることを確認

2. **ツールが表示されない場合**
   - ブラウザのキャッシュをクリア（F5またはCtrl + F5）
   - OpenWebUIを再起動
   - Tool Serverを再起動

---

## 🔥 レミ先輩の推奨

### 優先度1: OpenWebUIの起動確認

1. **OpenWebUIが起動しているか確認**
   - http://localhost:3001 にアクセス
   - 起動していない場合、起動

### 優先度2: Tool Serverの登録

1. **OpenWebUIの「外部ツール」設定画面でTool Serverを登録**
   - これが最重要
   - 登録後、接続状態を確認

### 優先度3: 設定の確認

1. **「関数呼び出し」の設定を確認**
   - 「有効 (Enabled)」または「自動 (Auto)」に設定

2. **接続状態を確認**
   - 「Connected」になっているか確認

### 優先度4: 動作確認

1. **ツールの表示確認**
   - 「ツールの選択」ドロップダウンで確認

2. **動作テスト**
   - チャットで「dockerコンテナの状態を確認して」と送信
   - LLMが`service_status`ツールを呼び出すことを確認

---

## 📋 確認チェックリスト

- [ ] OpenWebUIが起動中（http://localhost:3001）
- [ ] Tool Serverが起動中（http://localhost:9503/health）
- [ ] OpenAPI仕様が取得できる（http://localhost:9503/openapi.json）
- [ ] OpenWebUIの「外部ツール」設定画面でTool Serverを登録
- [ ] Tool Serverの接続状態が「Connected」
- [ ] 「関数呼び出し」が「有効 (Enabled)」または「自動 (Auto)」に設定
- [ ] 「ツールの選択」ドロップダウンでツールが表示される
- [ ] チャットでツールの動作確認

---

**レミ先輩モード**: どんどん進めよう！まずはOpenWebUIを起動して、Tool Serverを登録することが最重要！🔥
