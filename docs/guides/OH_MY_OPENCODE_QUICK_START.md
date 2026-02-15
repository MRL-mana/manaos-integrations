# 🚀 OH MY OPENCODE × ManaOS クイックスタート

## ⚠️ 重要な理解

**OH MY OPENCODE自体はAPIキーを発行しません。**

OH MY OPENCODEは**既存のLLMプロバイダのAPIキーを使用するハーネス**です。

---

## 🎯 最短ルート（推奨: OpenRouter）

### ステップ1: OpenRouterでAPIキーを取得

1. **OpenRouterにアクセス**
   ```
   https://openrouter.ai/
   ```

2. **アカウント作成・ログイン**
   - Sign Up（無料）
   - メール認証

3. **APIキーを作成**
   - Dashboard → Keys → Create Key
   - キー名: `ManaOS Integration`
   - **生成されたキーをコピー**（一度しか表示されない）

---

### ステップ2: 環境変数に設定

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openrouter_key_here" -Provider "OpenRouter"
```

---

### ステップ3: 設定ファイルを確認

`oh_my_opencode_config.yaml`が以下のようになっていることを確認：

```yaml
api:
  base_url: "https://openrouter.ai/api/v1"
  api_key: "${OPENROUTER_API_KEY}"
```

---

### ステップ4: 統合APIサーバーを起動

```powershell
python unified_api_server.py
```

---

### ステップ5: 動作確認

```powershell
# ヘルスチェック
curl http://127.0.0.1:9510/health

# OH MY OPENCODE実行テスト
curl -X POST http://127.0.0.1:9510/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{\"task_description\": \"PythonでHello Worldを出力するコードを生成してください\", \"mode\": \"normal\", \"task_type\": \"code_generation\"}'
```

---

## 🔄 代替ルート

### OpenAIを使用する場合

```powershell
# 1. OpenAIでAPIキーを取得（https://platform.openai.com/）
# 2. 環境変数に設定
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openai_key_here" -Provider "OpenAI"

# 3. 設定ファイルを更新
# oh_my_opencode_config.yaml の api.base_url を "https://api.openai.com/v1" に変更
```

### Anthropicを使用する場合

```powershell
# 1. AnthropicでAPIキーを取得（https://console.anthropic.com/）
# 2. 環境変数に設定
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_anthropic_key_here" -Provider "Anthropic"

# 3. 設定ファイルを更新
# oh_my_opencode_config.yaml の api.base_url を "https://api.anthropic.com/v1" に変更
```

---

## 📊 プロバイダ比較

| プロバイダ | 推奨度 | 理由 |
|----------|--------|------|
| **OpenRouter** | ⭐⭐⭐⭐⭐ | ManaOS統合に最適、複数モデル管理 |
| **OpenAI** | ⭐⭐⭐⭐ | 安定、ドキュメント豊富 |
| **Anthropic** | ⭐⭐⭐ | 高品質、コスト高 |

---

## ⚠️ トラブルシューティング

### APIキーが認識されない

1. **新しいPowerShellウィンドウを開く**
   - 環境変数の変更を反映するため

2. **環境変数の確認**
   ```powershell
   $env:OPENROUTER_API_KEY  # または OPENAI_API_KEY / ANTHROPIC_API_KEY
   ```

3. **設定ファイルの確認**
   - `oh_my_opencode_config.yaml`の`api.base_url`が正しいか確認

---

## 📝 詳細情報

- **プロバイダ設定ガイド**: `OH_MY_OPENCODE_PROVIDER_SETUP.md`
- **APIキー設定手順**: `OH_MY_OPENCODE_API_KEY_SETUP_CORRECTED.md`
- **統合状況**: `OH_MY_OPENCODE_INTEGRATION_STATUS.md`

---

**最終更新:** 2024年12月

