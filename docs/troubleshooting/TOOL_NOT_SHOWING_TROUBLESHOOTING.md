# 🔧 ツールが表示されない場合のトラブルシューティング

## ❌ 問題

「ツールの選択」ドロップダウンにTool Serverのツールが表示されない。

## 🔍 原因

モデルが原因ではない可能性が高いです。以下の原因が考えられます：

1. **Tool ServerがOpenWebUIに正しく登録されていない（最も可能性が高い）**
2. **OpenWebUIがTool ServerのOpenAPI仕様を取得できていない**
3. **Function Callingの設定（ネイティブモード）が問題**
4. **CORSの問題**

## ✅ 解決方法

### Step 1: OpenWebUIの設定画面を開く

1. **右上の設定アイコン（⚙️）をクリック**
2. **左メニューから「External Tools」または「Tool Servers」タブを選択**

### Step 2: Tool Serverが登録されているか確認

1. **`http://127.0.0.1:9503` が登録されているか確認**
   - 登録されている場合、接続状態を確認（「Connected」になっているか）
   - 登録されていない、または接続されていない場合、Step 3に進む

### Step 3: Tool Serverを登録（または再登録）

1. **「Add Tool」または「ツールを追加」をクリック**
2. **以下の情報を入力：**

   ```
   Name: manaOS Tool Server
   URL: http://127.0.0.1:9503
   OpenAPI Spec: ON（チェックを入れる）
   OpenAPI Spec URL: http://127.0.0.1:9503/openapi.json
   ```

3. **「Save」をクリック**

### Step 4: 接続状態を確認

1. **Tool Serverが「Connected」になっているか確認**
2. **接続されていない場合、以下を確認：**
   - Tool Serverが起動中か確認（http://127.0.0.1:9503/health）
   - OpenAPI仕様が取得できるか確認（http://127.0.0.1:9503/openapi.json）
   - CORS設定が正しいか確認

### Step 5: チャットコントロールセクションを再確認

1. **チャット画面に戻る**
2. **「ツールの選択」ドロップダウンを開く**
3. **Tool Serverのツール（`service_status`, `check_errors`, `generate_image`）が表示されることを確認**

## 🔍 モデルについて

### qwen2.5-coder-7b-instruct

- **Function Calling対応**: ✅ 対応しています
- **モデルが原因ではない可能性が高い**

### 他のモデルを試す場合

もし他のモデルを試したい場合：

1. **より大きなモデルを試す**
   - `qwen2.5-coder-14b-instruct` など

2. **Ollamaのモデルを試す**
   - Ollamaで利用可能なモデルを試す

## 🔍 確認コマンド

### Tool Serverの状態を確認

```powershell
# 健康状態を確認
Invoke-RestMethod -Uri "http://127.0.0.1:9503/health"

# OpenAPI仕様を確認
Invoke-RestMethod -Uri "http://127.0.0.1:9503/openapi.json"
```

### OpenWebUIのログを確認

ブラウザの開発者ツール（F12）で：
- Networkタブ → `/api/v1/tools/` のリクエストを確認
- Consoleタブ → エラーメッセージを確認

## 🔥 レミ先輩のアドバイス

### ✅ やるべき

1. **Tool ServerがOpenWebUIに正しく登録されているか確認**
   - 最も可能性が高い原因

2. **OpenAPI仕様が正しく取得できるか確認**
   - Tool Serverが正常に動作しているか確認

3. **Function Callingの設定を確認**
   - 「ネイティブ」モードが正しく設定されているか確認

4. **ブラウザの開発者ツールでエラーを確認**
   - NetworkタブやConsoleタブでエラーがないか確認

### ❌ やっちゃダメ

- モデルが原因だと決めつける（qwen2.5-coder-7b-instructはFunction Callingに対応している）
- Tool Serverの登録状況を確認せずに他の原因を探す
- 設定を確認せずに再起動する

## 📋 チェックリスト

- [ ] Tool ServerがOpenWebUIに登録されている
- [ ] Tool Serverが「Connected」になっている
- [ ] OpenAPI仕様が正しく取得できる（http://127.0.0.1:9503/openapi.json）
- [ ] Tool Serverが正常に動作している（http://127.0.0.1:9503/health）
- [ ] Function Callingが「ネイティブ」モードに設定されている
- [ ] 「ツールの選択」ドロップダウンを開いている
- [ ] ブラウザの開発者ツールでエラーがない

## 🎯 次のステップ

上記のチェックリストを確認した後、再度「ツールの選択」ドロップダウンを開いて、Tool Serverのツールが表示されることを確認してください。

---

**レミ先輩モード**: モデルが原因ではない可能性が高いです！Tool Serverの登録状況を確認しましょう！🔥
