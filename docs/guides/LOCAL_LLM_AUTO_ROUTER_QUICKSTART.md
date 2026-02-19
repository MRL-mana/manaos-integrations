# VS CodeローカルLLM自動振り分け（OpenAI互換）クイックスタート

## 1) ルーター起動

PowerShell で実行:

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_manaos_llm_openai_router.ps1 -LlmServer ollama -Port 5211
```

LM Studioを使う場合:

```powershell
.\start_manaos_llm_openai_router.ps1 -LlmServer lm_studio -Port 5211
```

## 2) VS Code / Cursor 側設定

OpenAI互換のカスタムモデルを1つ追加します。

- Base URL: `http://127.0.0.1:5211/v1`
- API Key: 任意（例: `local`）
- Model: `auto-local`

この `auto-local` が、内部でプロンプト難易度を見てモデルを自動選択します。

### Continue を使う場合

このリポジトリに `/.continue/config.json` を作成済みです。Continue 側でワークスペースを開けば `auto-local` を利用できます。

### Cline を使う場合

次を実行すると、Cursor/VS Code 両方の `cline_mcp_settings.json` に `llm-routing` をバックアップ付きで反映します。

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\setup_cline_local_llm_router.ps1
```

## 3) 利用可能モデル確認

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/models"
```

## 4) 動作テスト

```powershell
$body = @{
  model = "auto-local"
  messages = @(
    @{ role = "system"; content = "You are a coding assistant." },
    @{ role = "user"; content = "PythonでCSVを読み込んで合計を計算する関数を書いて" }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/chat/completions" -Method Post -ContentType "application/json" -Body $body
```

または PowerShell スクリプトで簡易テスト:

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\test_auto_local_chat.ps1
```

## 4.5) ManaOS フル統合スモークテスト

ManaOS本体ヘルス + OpenAI互換ルーター + auto-local + Tool Server統合をまとめて確認できます。

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\run_manaos_full_smoke.ps1
```

## 5) 手動固定も可能

`model` に実在モデル名を入れると固定ルーティングになります。

例:

- `qwen2.5-coder:7b`
- `qwen2.5-coder:14b`
- `qwen2.5-coder:32b`

## 補足

- 既定は `LLM_SERVER=ollama`。LM Studioを使う場合だけ `-LlmServer lm_studio` を指定。
- 既存API (`/api/llm/*`) はそのまま利用できます。
- `start_manaos_llm_openai_router.ps1` で `-Port 5111` を指定してポート使用中の場合、既存の 5211 ルーターが起動済みなら自動で再利用されます。
