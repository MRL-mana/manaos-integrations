# 🔧 Tool Serverが呼び出されない場合のトラブルシューティング

## ❌ 問題

LLMがTool Serverを呼び出さず、コマンドの説明を返してしまう。

## 🔍 原因

Function Callingが有効になっていない可能性が高いです。

## ✅ 解決方法

### Step 1: OpenWebUIの設定でFunction Callingを有効にする

1. **OpenWebUIの設定画面を開く**
   - 右上の設定アイコン（⚙️）をクリック

2. **「Chat」または「モデル設定」を確認**
   - 左側のメニューから「Chat」または「Models」を選択

3. **「Function Call」を有効にする**
   - 「Function Call」または「Tool Use」のトグルをONにする
   - 「Enable Function Calling」がONになっているか確認

### Step 2: チャット画面でFunction Callingを有効にする

1. **新しいチャットを開始**
   - 新しいチャットセッションを開始

2. **モデル設定を確認**
   - チャット画面の上部で使用するモデルを選択
   - `qwen2.5-coder-7b-instruct` がFunction Callingに対応しているか確認

3. **Function Callボタンを確認**
   - チャット画面に「Function Call」や「Tools」ボタンが表示されているか確認
   - 表示されている場合は、それをクリックして有効にする

### Step 3: Tool Serverが正しく認識されているか確認

1. **Tool Serverの状態を確認**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:9503/health"
   ```

2. **OpenAPI仕様が正しく取得できるか確認**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:9503/openapi.json"
   ```

3. **OpenWebUIの設定画面でTool Serverが正しく登録されているか確認**
   - 設定画面 → 「External Tools」または「Tool Servers」
   - `http://localhost:9503` が登録されているか確認
   - ステータスが「Connected」になっているか確認

### Step 4: モデルを確認

`qwen2.5-coder-7b-instruct` はFunction Callingに対応していますが、以下の点を確認：

1. **モデルが正しく読み込まれているか確認**
   - Ollamaでモデルが利用可能か確認
   ```powershell
   docker exec ollama ollama list
   ```

2. **モデルのバージョンを確認**
   - 最新バージョンを使用しているか確認

### Step 5: システムプロンプトを確認

OpenWebUIのシステムプロンプトでTool Serverの使用を促す：

```
あなたはTool Serverを使用できます。以下のツールが利用可能です：
- service_status: dockerコンテナの状態を確認
- check_errors: 最近のログを確認してエラーを検出
- generate_image: ComfyUIで画像を生成

ユーザーからの要求に対して、適切なツールを使用してください。
```

## 🔥 レミ先輩のアドバイス

### ✅ やるべき

1. **Function Callingを必ず有効にする**
   - OpenWebUIの設定でFunction CallingをONにする
   - チャット画面でFunction Callingを有効にする

2. **Tool Serverが正しく動作しているか確認**
   - 健康状態を確認
   - OpenAPI仕様が正しく取得できるか確認

3. **システムプロンプトでTool Serverの使用を促す**
   - LLMにTool Serverを使用するよう明確に指示

### ❌ やっちゃダメ

- Function Callingを有効にせずにツールを使おうとする
- Tool Serverが動作していないのにツールを呼び出そうとする
- システムプロンプトでTool Serverについて言及しない

## 📋 確認チェックリスト

- [ ] OpenWebUIの設定でFunction Callingが有効になっている
- [ ] チャット画面でFunction Callingが有効になっている
- [ ] Tool Serverが起動中（http://localhost:9503）
- [ ] OpenAPI仕様が正しく取得できる
- [ ] Tool ServerがOpenWebUIに正しく登録されている
- [ ] 使用しているモデルがFunction Callingに対応している
- [ ] システムプロンプトでTool Serverの使用を促している

## 🎯 次のステップ

上記の手順を実行した後、再度チャットで以下を試してください：

```
dockerコンテナの状態を確認して
```

LLMがTool Serverを呼び出すことを確認してください。

---

**レミ先輩モード**: Function Callingを有効にしないと、LLMはツールを使いません！設定を確認しましょう！🔥
