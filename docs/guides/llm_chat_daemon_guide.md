# ローカルLLMチャット常時起動デーモンガイド

## 📋 概要

ローカルLLMチャットインターフェース（AI Model Hub、RAG API Serverなど）を常時監視し、停止時に自動的に再起動するデーモンです。

## 🎯 監視対象サービス

| サービス | ポート | 優先度 | デフォルト |
|---|---|---|---|
| **AI Model Hub** | 5080 | High | ✅ 有効 |
| **RAG API Server** | 5057 | High | ✅ 有効 |
| **Unified Portal** | 5000 | Medium | ❌ 無効 |
| **AI Assistant Chatbot** | 5074 | Low | ❌ 無効 |

## 🚀 使用方法

### 1. デーモンを起動

```powershell
cd Scripts
.\llm_chat_daemon.ps1 -Start
```

### 2. 状態確認

```powershell
.\llm_chat_daemon.ps1 -Status
```

### 3. デーモンを停止

```powershell
.\llm_chat_daemon.ps1 -Stop
```

### 4. デーモンを再起動

```powershell
.\llm_chat_daemon.ps1 -Restart
```

### 5. 自動起動を設定

```powershell
.\setup_llm_chat_autostart.ps1
```

これで、Windows起動時に自動的にデーモンが起動します。

## 🔧 設定のカスタマイズ

### 監視間隔の変更

```powershell
.\llm_chat_daemon.ps1 -Start -CheckInterval 30  # 30秒ごとにチェック
```

### サービスを有効/無効にする

`llm_chat_daemon.ps1` の `$script:Services` セクションを編集：

```powershell
$script:Services = @{
    "unified_portal" = @{
        "Name" = "Unified Portal"
        "Port" = 5000
        "Script" = "Systems\konoha_migration\manaos_unified_system\services\unified_portal.py"
        "Enabled" = $true  # 有効にする
        "Priority" = "Medium"
    }
}
```

## 📊 動作確認

### デーモンの状態確認

```powershell
.\llm_chat_daemon.ps1 -Status
```

出力例：
```
=== ローカルLLMチャットデーモン状態 ===

デーモン: 実行中 (PID: 12345)

サービス状態:
  AI Model Hub: 実行中 (ポート 5080)
  RAG API Server: 実行中 (ポート 5057)
  Unified Portal: 停止中 (ポート 5000) (無効)
  AI Assistant Chatbot: 停止中 (ポート 5074) (無効)
```

### ログの確認

```powershell
Get-Content logs\llm_chat_daemon.log -Tail 50
```

## 🎯 推奨設定

### 基本設定（推奨）

- **AI Model Hub**: 有効（Web UI付き、使いやすい）
- **RAG API Server**: 有効（RAG機能付き、高精度）
- **Unified Portal**: 無効（既に起動している可能性が高い）
- **AI Assistant Chatbot**: 無効（オプション）

### 監視間隔

- **デフォルト**: 60秒
- **推奨**: 60秒（バランスが良い）
- **高速監視**: 30秒（より迅速な再起動）
- **低負荷**: 120秒（リソース節約）

## 🔍 トラブルシューティング

### サービスが起動しない場合

1. **ポートが使用中か確認**
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 5080
   ```

2. **スクリプトパスを確認**
   ```powershell
   Test-Path "Systems\konoha_migration\manaos_unified_system\services\ai_model_hub.py"
   ```

3. **Pythonが利用可能か確認**
   ```powershell
   python --version
   ```

### デーモンが停止する場合

1. **ログを確認**
   ```powershell
   Get-Content logs\llm_chat_daemon.log -Tail 100
   ```

2. **手動でサービスを起動して確認**
   ```powershell
   python Systems\konoha_migration\manaos_unified_system\services\ai_model_hub.py
   ```

## 📝 自動起動の設定

### Windows起動時に自動起動

```powershell
.\setup_llm_chat_autostart.ps1
```

これで、Windows起動時に自動的にデーモンが起動し、チャットインターフェースが利用可能になります。

### 自動起動を無効化

```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\LLMChatDaemon.lnk"
```

## 🎯 使用例

### 1. デーモンを起動して常時監視

```powershell
# デーモンを起動
.\llm_chat_daemon.ps1 -Start

# 状態確認
.\llm_chat_daemon.ps1 -Status

# ブラウザでAI Model Hubを開く
Start-Process "http://127.0.0.1:5080"
```

### 2. 自動起動を設定

```powershell
# 自動起動を設定
.\setup_llm_chat_autostart.ps1

# 次回のログイン時に自動起動します
```

### 3. ログを確認

```powershell
# 最新のログを確認
Get-Content logs\llm_chat_daemon.log -Tail 20

# エラーのみを確認
Get-Content logs\llm_chat_daemon.log | Select-String "ERROR"
```

## 📊 メリット

### 常時起動型のメリット

1. **いつでも会話可能** - ブラウザを開くだけで会話開始
2. **自動復旧** - サービスが停止しても自動的に再起動
3. **監視機能** - サービスの状態を常に監視
4. **ログ記録** - すべての動作をログに記録

### 手動起動との比較

| 項目 | 常時起動型 | 手動起動 |
|---|---|---|
| **起動時間** | 即座に利用可能 | 起動が必要 |
| **自動復旧** | ✅ あり | ❌ なし |
| **リソース使用** | やや多い | 少ない |
| **利便性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🎯 まとめ

**常時起動型デーモンを使う場合:**
- いつでも会話したい
- 自動復旧が必要
- 監視機能が欲しい

**手動起動を使う場合:**
- 必要な時だけ起動したい
- リソースを節約したい
- 起動時間は気にしない

**推奨:**
- **AI Model Hub** と **RAG API Server** は常時起動推奨
- 自動起動を設定して、Windows起動時に自動的に利用可能に



