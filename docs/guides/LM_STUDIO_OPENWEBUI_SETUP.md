# 🚀 LM Studio + Open WebUI セットアップガイド

**作成日**: 2025-01-28  
**構成**: 母艦でLM Studio起動 → Open WebUI（Docker）から使用

---

## ✅ 前提条件

- ✅ LM Studioがインストール済み
- ✅ Docker & Docker Composeが利用可能
- ✅ ポート3000, 1234が利用可能

---

## 📋 セットアップ手順

### ステップ1: LM Studioでサーバーを起動

1. **LM Studioを開く**
2. **「Server」タブを探す**
   - 左サイドバーの **🖧 Server** アイコンをクリック
   - または上部メインナビゲーションの「Server」タブ
3. **サーバーをONにする**
   - 「Start Server」または「サーバーを開始」をクリック
4. **URLとポートを確認**
   - 通常は以下のいずれか：
     - `http://localhost:1234`
     - `http://127.0.0.1:1234`
   - **OpenAI Compatible API** と表示されていればOK

---

### ステップ2: Docker ComposeでOpen WebUIを起動

```powershell
# docker-compose.always-ready-llm.ymlがあるディレクトリに移動
cd C:\Users\mana4\Desktop\manaos_integrations

# Open WebUIを含む全サービスを起動
docker-compose -f docker-compose.always-ready-llm.yml up -d

# ログ確認
docker-compose -f docker-compose.always-ready-llm.yml logs -f openwebui
```

---

### ステップ3: Open WebUIにアクセス

1. **ブラウザで開く**
   ```
   http://localhost:3001
   ```
   ⚠️ **注意**: ポート3000が既に使用されている場合（例：Grafana）、ポート3001で起動します。

2. **初回ログイン**
   - 初回はアカウント作成画面が表示されます
   - ユーザー名とパスワードを設定

---

### ステップ4: LM Studioモデルを選択

1. **Open WebUIの設定画面を開く**
   - 右上の設定アイコン（⚙️）をクリック

2. **「Connections」または「モデル設定」を開く**

3. **LM Studioを追加**
   - 「Add Connection」または「接続を追加」
   - **Connection Type**: OpenAI Compatible
   - **Base URL**: `http://host.docker.internal:1234/v1`
   - **API Key**: `lm-studio`（任意の文字列でOK）

4. **モデルを選択**
   - LM Studioでロードしたモデルが表示されます
   - 使用したいモデルを選択

---

## 🎯 動作確認

### LM Studioのサーバー状態確認

```powershell
# LM StudioのAPIが応答するか確認
curl http://localhost:1234/v1/models
```

### Open WebUIからLM Studioに接続確認

1. Open WebUIでチャットを開始
2. モデル選択でLM Studioのモデルを選ぶ
3. メッセージを送信して応答を確認

---

## 🔧 トラブルシューティング

### 問題1: Open WebUIからLM Studioに接続できない

**原因**: Dockerコンテナからホストマシンの`localhost:1234`にアクセスできない

**解決策**:
1. `docker-compose.always-ready-llm.yml`の`openwebui`サービスに以下が含まれているか確認：
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   environment:
     - OPENAI_API_BASE_URL=http://host.docker.internal:1234/v1
   ```

2. LM Studioのサーバーが実際に起動しているか確認
   - LM Studioの「Server」タブで「Running」と表示されているか

3. ポート1234が正しいか確認
   - LM Studioの設定でポート番号を変更した場合は、`docker-compose.always-ready-llm.yml`のポート番号も変更

### 問題2: LM Studioの「Server」タブが見つからない

**解決策**: `WHERE_IS_SERVER_TAB.md`を参照

1. 左サイドバーの **🖧 Server** アイコンを探す
2. 見つからない場合は、LM Studioを最新版に更新
3. 代替方法: 「Settings」→「Developer」タブで「ローカル LLM サービスを有効にする」にチェック

### 問題3: OllamaとLM Studioの両方を使いたい

**解決策**: Open WebUIは両方に対応しています

- **Ollama**: `http://ollama:11434`（コンテナ内から）
- **LM Studio**: `http://host.docker.internal:1234/v1`（ホストマシンから）

両方の接続を追加すれば、モデル選択時に両方が表示されます。

---

## 📊 構成図

```
┌─────────────────┐
│   LM Studio     │  ← ホストマシンで起動（ポート1234）
│  (localhost)    │
└────────┬────────┘
         │
         │ http://host.docker.internal:1234/v1
         │
┌────────▼─────────────────────────────┐
│         Docker Network              │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  Open WebUI  │  │   Ollama    │ │
│  │  (ポート3000) │  │ (ポート11434)│ │
│  └──────────────┘  └─────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## 🎉 完了！

これで以下が利用可能になりました：

- ✅ **Open WebUI**: `http://localhost:3001`
- ✅ **LM Studio**: `http://localhost:1234`
- ✅ **Ollama**: `http://localhost:11434`
- ✅ **n8n**: `http://localhost:5678`

Open WebUIからLM StudioとOllamaの両方のモデルを使用できます！

---

## 📝 補足情報

### ポート番号一覧

| サービス | ポート | 用途 |
|---------|--------|------|
| Open WebUI | 3001 | Web UI（3000が使用中の場合は3001） |
| LM Studio | 1234 | OpenAI互換API |
| Ollama | 11434 | Ollama API |
| n8n | 5678 | ワークフローエンジン |
| Redis | 6379 | キャッシュ |
| Traefik | 80, 443, 8080 | リバースプロキシ |

### 環境変数のカスタマイズ

`.env`ファイルを作成して、以下の変数を設定できます：

```env
# LM Studioのポートを変更した場合
LM_STUDIO_PORT=1234

# Open WebUIのシークレットキー
WEBUI_SECRET_KEY=your-secret-key-here

# n8n認証情報
N8N_USER=admin
N8N_PASSWORD=your-password
```

---

## 🔄 サービス管理

### 全サービス起動
```powershell
docker-compose -f docker-compose.always-ready-llm.yml up -d
```

### 全サービス停止
```powershell
docker-compose -f docker-compose.always-ready-llm.yml down
```

### Open WebUIのみ再起動
```powershell
docker-compose -f docker-compose.always-ready-llm.yml restart openwebui
```

### ログ確認
```powershell
# Open WebUIのログ
docker-compose -f docker-compose.always-ready-llm.yml logs -f openwebui

# 全サービスのログ
docker-compose -f docker-compose.always-ready-llm.yml logs -f
```

