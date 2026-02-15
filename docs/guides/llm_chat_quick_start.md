# ローカルLLMチャット クイックスタート

## 🚀 すぐに会話を始める

### 方法1: 一括起動スクリプト（最も簡単）

```powershell
.\Scripts\start_llm_chat_services.ps1
```

これで、AI Model HubとRAG API Serverが自動的に起動します。

### 方法2: ブラウザで開く

```powershell
# AI Model Hubを開く
Start-Process "http://127.0.0.1:5080"

# RAG API Serverの状態確認
Start-Process "http://127.0.0.1:5057"
```

### 方法3: 手動起動

```powershell
# AI Model Hub
python Systems\konoha_migration\manaos_unified_system\services\ai_model_hub.py

# RAG API Server
python Systems\konoha_migration\server_projects\projects\automation\rag_api_server.py
```

## ✅ 自動起動設定済み

次回のWindows起動時に自動的にチャットサービスが利用可能になります。

## 📊 現在の状態確認

```powershell
# ポート確認
Test-NetConnection -ComputerName localhost -Port 5080
Test-NetConnection -ComputerName localhost -Port 5057

# デーモン状態確認
.\Scripts\llm_chat_daemon.ps1 -Status
```

## 🎯 使い方

1. **AI Model Hub** (`http://127.0.0.1:5080`)
   - Web UIで直接会話
   - モデル選択可能
   - テンプレート機能あり

2. **RAG API Server** (`http://127.0.0.1:5057`)
   - API経由でRAG機能付き会話
   - ドキュメント検索＋回答

## 🔧 トラブルシューティング

### サービスが起動しない場合

```powershell
# Pythonが利用可能か確認
python --version

# スクリプトパスを確認
Test-Path "Systems\konoha_migration\manaos_unified_system\services\ai_model_hub.py"
```

### ポートが使用中の場合

```powershell
# 使用中のプロセスを確認
netstat -ano | Select-String ":5080|:5057"
```



