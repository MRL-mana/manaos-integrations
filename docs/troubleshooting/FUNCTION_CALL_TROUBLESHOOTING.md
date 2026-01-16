# 🔧 関数呼び出しが動作しない場合のトラブルシューティング

**問題**: LLMがmanaOS統合APIの関数を呼び出さない

---

## 🔍 確認事項

### 1. 「関数呼び出し」パラメータの設定

チャットコントロール画面で確認：

- 「**関数呼び出し (Function Call)**」のパラメータが「**デフォルト**」ではなく、**有効**になっているか確認
- 「デフォルト」の場合は、クリックして「**有効**」または「**自動**」に変更

### 2. Open WebUIのツール一覧を確認

1. 設定画面を開く
2. 「**External Tools**」タブを選択
3. `http://host.docker.internal:9500` の接続が表示されているか確認
4. 接続をクリックして、ツール一覧に以下の関数が表示されているか確認：
   - `generateImageComfyUI`
   - `uploadToGoogleDrive`
   - `createObsidianNote`
   - `searchCivitAIModels`

### 3. モデルのFunction Calling対応確認

使用しているモデル（`qwen2.5-coder-7b-instruct`）がFunction Callingに対応しているか確認：

- **qwen2.5-coder-7b-instruct**: Function Callingに対応しているはずですが、モデルによって異なる場合があります
- **qwen2.5-coder-14b-instruct** を試してみる

---

## 🔧 解決方法

### 方法1: 関数呼び出しを明示的に有効化

1. **チャットコントロール画面を開く**
2. 「**関数呼び出し (Function Call)**」パラメータをクリック
3. 「**デフォルト**」から「**有効**」または「**自動**」に変更

### 方法2: システムプロンプトで明示的に指示

1. **設定画面を開く**
2. 「**一般**」タブを選択
3. 「**システムプロンプトをここに入力**」に以下を追加：

```
画像生成が必要な場合は、generateImageComfyUI関数を使用してください。
ファイルアップロードが必要な場合は、uploadToGoogleDrive関数を使用してください。
Obsidianノート作成が必要な場合は、createObsidianNote関数を使用してください。

関数を呼び出す際は、必ずFunction Calling機能を使用してください。
```

### 方法3: モデルを変更してみる

1. **チャット画面でモデルを変更**
2. より大きなモデルを試す（例：`qwen2.5-coder-14b-instruct`）
3. または、Ollamaのモデルを試す

### 方法4: 直接APIを呼び出す（テスト用）

チャットで以下のように明示的に指示：

```
generateImageComfyUI関数を呼び出して、プロンプト「美しい風景」で画像を生成してください
```

---

## 📋 確認コマンド

### OpenAPI仕様の確認

```powershell
curl http://localhost:9500/openapi.json
```

### Open WebUIのツール一覧確認

ブラウザの開発者ツール（F12）で：
```
Network タブ → /api/v1/tools/ のリクエストを確認
```

---

## 💡 補足

Open WebUIのExternal Toolsは、OpenAPI仕様からツールを自動的に認識しますが、LLMが実際にツールを呼び出すかどうかは、以下の要因に依存します：

1. **モデルのFunction Calling対応**: モデルがFunction Callingに対応している必要があります
2. **関数呼び出しパラメータ**: チャットコントロール画面で有効になっている必要があります
3. **プロンプトの内容**: LLMがツールを使用すべきと判断する必要があります

---

**まず、「関数呼び出し」パラメータを「有効」に設定して試してください！**
