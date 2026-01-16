# 🔑 OH MY OPENCODE APIキー設定手順（正しい理解）

## ⚠️ 重要な理解

**OH MY OPENCODE自体はAPIキーを発行しません。**

OH MY OPENCODEは**既存のLLMプロバイダのAPIキーを使用するハーネス**です。

つまり：
- ❌ 「OH MY OPENCODE APIキー」は存在しない
- ✅ 「OpenAI / Anthropic / OpenRouter などのAPIキー」を使用する

---

## 🎯 推奨ルート（ManaOS向け）

### ルートA: OpenRouterでまとめて管理（推奨）

**メリット:**
- ✅ 複数モデルを1つのキーで管理
- ✅ モデル切り替えが簡単
- ✅ コスト管理が一元化
- ✅ ManaOSのLLMルーティングと相性が良い

**手順:**

1. **OpenRouterにアクセス**
   - https://openrouter.ai/
   - アカウント作成（無料）

2. **APIキーを作成**
   - Dashboard → Keys → Create Key
   - キー名を入力（例: `ManaOS Integration`）
   - 生成されたキーをコピー

3. **環境変数に設定**
   ```powershell
   # OpenRouter APIキー
   [System.Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", "your_openrouter_key_here", "User")
   ```

4. **OH MY OPENCODE設定を更新**
   - `oh_my_opencode_config.yaml`でOpenRouterを使用するように設定

---

### ルートB: OpenAIから開始（安定）

**メリット:**
- ✅ 最も安定している
- ✅ ドキュメントが豊富
- ✅ エコシステムが成熟

**手順:**

1. **OpenAIにアクセス**
   - https://platform.openai.com/
   - アカウント作成・ログイン

2. **APIキーを作成**
   - API Keys → Create new secret key
   - キー名を入力（例: `ManaOS Integration`）
   - 生成されたキーをコピー（**重要**: 一度しか表示されない）

3. **環境変数に設定**
   ```powershell
   # OpenAI APIキー
   [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your_openai_key_here", "User")
   ```

---

### ルートC: Anthropic（Claude）から開始（高品質）

**メリット:**
- ✅ 高品質な出力
- ✅ 長いコンテキスト
- ⚠️ コストが高い

**手順:**

1. **Anthropicにアクセス**
   - https://console.anthropic.com/
   - アカウント作成・ログイン

2. **APIキーを作成**
   - API Keys → Create Key
   - キー名を入力（例: `ManaOS Integration`）
   - 生成されたキーをコピー

3. **環境変数に設定**
   ```powershell
   # Anthropic APIキー
   [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your_anthropic_key_here", "User")
   ```

---

## 🔧 OH MY OPENCODE設定の更新

### OpenRouterを使用する場合

`oh_my_opencode_config.yaml`を更新：

```yaml
api:
  base_url: "https://openrouter.ai/api/v1"  # OpenRouterのエンドポイント
  api_key: "${OPENROUTER_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

### OpenAIを使用する場合

```yaml
api:
  base_url: "https://api.openai.com/v1"  # OpenAIのエンドポイント
  api_key: "${OPENAI_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

### Anthropicを使用する場合

```yaml
api:
  base_url: "https://api.anthropic.com/v1"  # Anthropicのエンドポイント
  api_key: "${ANTHROPIC_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

---

## 🚀 推奨設定（ManaOS統合）

ManaOSには既にLLMルーティング機能があるため、**OpenRouter経由**が最も効率的です。

### 設定手順

1. **OpenRouter APIキーを取得**
   ```powershell
   # ブラウザで https://openrouter.ai/ にアクセス
   # Dashboard → Keys → Create Key
   ```

2. **環境変数に設定**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openrouter_key_here"
   ```
   
   または手動で：
   ```powershell
   [System.Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", "your_openrouter_key_here", "User")
   ```

3. **設定ファイルを更新**
   - `oh_my_opencode_config.yaml`の`api.base_url`をOpenRouterに変更

4. **ManaOS LLMルーティングと統合**
   - ManaOSのLLMルーティングがOpenRouter経由でモデルを選択
   - OH MY OPENCODEはOpenRouterのキーを使用

---

## 📊 各プロバイダの比較

| プロバイダ | メリット | デメリット | 推奨度 |
|----------|---------|-----------|--------|
| **OpenRouter** | 複数モデル統合、コスト管理、ManaOS統合に最適 | 追加レイヤー | ⭐⭐⭐⭐⭐ |
| **OpenAI** | 安定、ドキュメント豊富 | 単一プロバイダ | ⭐⭐⭐⭐ |
| **Anthropic** | 高品質、長いコンテキスト | コスト高 | ⭐⭐⭐ |

---

## ⚠️ 重要な注意事項

1. **APIキーは一度しか表示されない**
   - 必ずコピーして安全な場所に保存
   - 漏洩した場合は即座に削除・再生成

2. **コスト管理**
   - OpenRouter: ダッシュボードで一元管理
   - OpenAI: Usage & Billingで確認
   - Anthropic: Usageで確認

3. **ManaOS統合**
   - ManaOSのLLMルーティング機能と統合することで、最適なモデルを自動選択可能

---

## 🎯 次のステップ

**推奨: OpenRouterから開始**

理由：
- ✅ ManaOSのLLMルーティングと相性が良い
- ✅ 複数モデルを1つのキーで管理
- ✅ コスト管理が簡単

**手順:**
1. OpenRouterでAPIキーを取得
2. 環境変数に設定
3. `oh_my_opencode_config.yaml`を更新
4. 統合APIサーバーを起動して動作確認

---

**最終更新:** 2024年12月
