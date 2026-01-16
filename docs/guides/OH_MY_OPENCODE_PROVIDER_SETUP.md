# 🔧 OH MY OPENCODE プロバイダ設定ガイド

## 🎯 重要な理解

**OH MY OPENCODE自体はAPIキーを発行しません。**

OH MY OPENCODEは**既存のLLMプロバイダのAPIキーを使用するハーネス**です。

---

## 📋 推奨ルート（ManaOS向け）

### ⭐ ルートA: OpenRouter（最推奨）

**なぜ推奨？**
- ✅ ManaOSのLLMルーティングと完全統合可能
- ✅ 複数モデルを1つのキーで管理
- ✅ コスト管理が一元化
- ✅ モデル切り替えが簡単

**手順:**

#### 1. OpenRouterでAPIキーを取得

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
   - 生成されたキーをコピー（**重要**: 一度しか表示されない）

#### 2. 環境変数に設定

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openrouter_key_here" -Provider "OpenRouter"
```

#### 3. 設定ファイルを更新

`oh_my_opencode_config.yaml`を編集：

```yaml
api:
  base_url: "https://openrouter.ai/api/v1"  # OpenRouterのエンドポイント
  api_key: "${OPENROUTER_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

#### 4. ManaOS LLMルーティングと統合

ManaOSのLLMルーティング機能がOpenRouter経由でモデルを自動選択します。

---

### ルートB: OpenAI（安定）

**メリット:**
- ✅ 最も安定している
- ✅ ドキュメントが豊富
- ✅ エコシステムが成熟

**手順:**

#### 1. OpenAIでAPIキーを取得

1. **OpenAIにアクセス**
   ```
   https://platform.openai.com/
   ```

2. **アカウント作成・ログイン**
   - Sign Up
   - メール認証・電話認証

3. **APIキーを作成**
   - API Keys → Create new secret key
   - キー名: `ManaOS Integration`
   - 生成されたキーをコピー（**重要**: 一度しか表示されない）

#### 2. 環境変数に設定

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openai_key_here" -Provider "OpenAI"
```

#### 3. 設定ファイルを更新

```yaml
api:
  base_url: "https://api.openai.com/v1"  # OpenAIのエンドポイント
  api_key: "${OPENAI_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

---

### ルートC: Anthropic（Claude）（高品質）

**メリット:**
- ✅ 高品質な出力
- ✅ 長いコンテキスト
- ⚠️ コストが高い

**手順:**

#### 1. AnthropicでAPIキーを取得

1. **Anthropicにアクセス**
   ```
   https://console.anthropic.com/
   ```

2. **アカウント作成・ログイン**
   - Sign Up
   - メール認証

3. **APIキーを作成**
   - API Keys → Create Key
   - キー名: `ManaOS Integration`
   - 生成されたキーをコピー

#### 2. 環境変数に設定

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_anthropic_key_here" -Provider "Anthropic"
```

#### 3. 設定ファイルを更新

```yaml
api:
  base_url: "https://api.anthropic.com/v1"  # Anthropicのエンドポイント
  api_key: "${ANTHROPIC_API_KEY}"  # 環境変数から取得
  timeout: 300.0
```

---

## 📊 プロバイダ比較表

| プロバイダ | メリット | デメリット | コスト | 推奨度 |
|----------|---------|-----------|--------|--------|
| **OpenRouter** | 複数モデル統合、ManaOS統合に最適 | 追加レイヤー | 中 | ⭐⭐⭐⭐⭐ |
| **OpenAI** | 安定、ドキュメント豊富 | 単一プロバイダ | 中 | ⭐⭐⭐⭐ |
| **Anthropic** | 高品質、長いコンテキスト | コスト高 | 高 | ⭐⭐⭐ |

---

## 🚀 推奨設定（ManaOS統合）

**推奨: OpenRouterから開始**

**理由:**
1. ManaOSのLLMルーティング機能と完全統合可能
2. 複数モデルを1つのキーで管理
3. コスト管理が一元化
4. モデル切り替えが簡単

**設定手順:**

```powershell
# 1. OpenRouterでAPIキーを取得（ブラウザで https://openrouter.ai/）
# 2. 環境変数に設定
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_openrouter_key_here" -Provider "OpenRouter"

# 3. 設定ファイルを更新
# oh_my_opencode_config.yaml の api.base_url を "https://openrouter.ai/api/v1" に変更

# 4. 統合APIサーバーを起動
python unified_api_server.py
```

---

## ⚠️ 重要な注意事項

1. **APIキーは一度しか表示されない**
   - 必ずコピーして安全な場所に保存
   - 漏洩した場合は即座に削除・再生成

2. **コスト管理**
   - OpenRouter: Dashboard → Usage で確認
   - OpenAI: Usage & Billing で確認
   - Anthropic: Usage で確認

3. **ManaOS統合**
   - ManaOSのLLMルーティング機能と統合することで、最適なモデルを自動選択可能

---

## 🔍 確認方法

### 環境変数の確認

```powershell
# OpenRouter
$env:OPENROUTER_API_KEY

# OpenAI
$env:OPENAI_API_KEY

# Anthropic
$env:ANTHROPIC_API_KEY
```

### 設定ファイルの確認

```yaml
# oh_my_opencode_config.yaml
api:
  base_url: "https://openrouter.ai/api/v1"  # または OpenAI / Anthropic
  api_key: "${OPENROUTER_API_KEY}"  # 対応する環境変数名
```

---

## 📝 次のステップ

1. ✅ **プロバイダを選択**（推奨: OpenRouter）
2. ✅ **APIキーを取得**
3. ✅ **環境変数に設定**
4. ✅ **設定ファイルを更新**
5. ✅ **統合APIサーバーを起動**
6. ✅ **動作確認**

---

**最終更新:** 2024年12月
