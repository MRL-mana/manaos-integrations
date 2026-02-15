# 🔗 manaOS統合API と Open WebUI の統合ガイド

**作成日**: 2025-01-06

---

## ✅ 現在の状態

### 起動中のサービス

- ✅ **manaOS統合API**: `http://127.0.0.1:9510`（起動中）
- ✅ **LM Studio**: `http://127.0.0.1:1234`（起動中、モデル利用可能）
- ✅ **Open WebUI**: `http://127.0.0.1:3001`（起動中）

### 接続状況

- ✅ **LM Studio**: Open WebUIに接続済み（設定画面で確認済み）
- ⚠️ **manaOS統合API**: Open WebUIとの統合が必要

---

## 🔧 Open WebUIでmanaOS統合APIを使う方法

### 方法1: External Tools（外部ツール）として統合

Open WebUIは外部ツール統合機能を持っています。manaOS統合APIを外部ツールとして追加できます。

#### ステップ1: Open WebUIの設定を開く

1. Open WebUIにログイン
2. 右上の⚙️（設定）アイコンをクリック
3. 左サイドバーで「**External Tools**」を選択

#### ステップ2: 外部ツールを追加

1. **「Add Tool」**または**「ツールを追加」**をクリック
2. 以下の情報を入力：

   - **Name（名前）**: `manaOS統合API`
   - **Description（説明）**: `manaOS統合システムへのアクセス`
  - **URL**: `http://host.docker.internal:9510`
   - **Method（メソッド）**: `POST`
   - **Headers（ヘッダー）**:
     ```json
     {
       "Content-Type": "application/json"
     }
     ```

#### ステップ3: チャットで使用

チャット画面で、外部ツールを呼び出してmanaOS統合APIの機能を使用できます。

---

### 方法2: Functions（関数）として統合

Open WebUIのFunctions機能を使って、manaOS統合APIのエンドポイントを関数として登録できます。

#### ステップ1: Functions設定を開く

1. 設定画面で「**Functions**」タブを選択
2. 「**Add Function**」をクリック

#### ステップ2: 関数を定義

manaOS統合APIの主要なエンドポイントを関数として登録：

**例1: 画像生成（ComfyUI）**
```json
{
  "name": "generate_image",
  "description": "ComfyUIを使って画像を生成します",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "画像生成のプロンプト"
      }
    },
    "required": ["prompt"]
  },
  "url": "http://host.docker.internal:9510/api/comfyui/generate",
  "method": "POST"
}
```

**例2: Google Driveアップロード**
```json
{
  "name": "upload_to_drive",
  "description": "ファイルをGoogle Driveにアップロードします",
  "parameters": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "アップロードするファイルのパス"
      }
    },
    "required": ["file_path"]
  },
  "url": "http://host.docker.internal:9510/api/google_drive/upload",
  "method": "POST"
}
```

---

## 📋 manaOS統合APIの主要エンドポイント

### 利用可能な機能

1. **ComfyUI統合** - 画像生成
   - `POST /api/comfyui/generate`

2. **Google Drive統合** - ファイル管理
   - `POST /api/google_drive/upload`
   - `GET /api/google_drive/list`

3. **Obsidian統合** - ノート作成
   - `POST /api/obsidian/create`

4. **LangChain統合** - LLMチャット
   - `POST /api/langchain/chat`

5. **CivitAI統合** - モデル検索
   - `GET /api/civitai/search`

---

## 🔍 動作確認

### manaOS統合APIの確認

```powershell
# ステータス確認
curl http://127.0.0.1:9510/api/status

# 利用可能なエンドポイント確認
curl http://127.0.0.1:9510/api/docs
```

### LM Studioの確認

```powershell
# モデル一覧
curl http://127.0.0.1:1234/v1/models

# Open WebUIコンテナから確認
docker exec open-webui curl http://host.docker.internal:1234/v1/models
```

---

## 🎯 使用例

### チャットでmanaOS機能を使う

1. Open WebUIのチャット画面を開く
2. モデルを選択（LM StudioまたはOllama）
3. 外部ツールまたはFunctionsを使ってmanaOS統合APIを呼び出す

**例**:
```
「ComfyUIで画像を生成して」→ Functionsが自動的にmanaOS統合APIを呼び出す
```

---

## 💡 補足情報

### Dockerコンテナからのアクセス

Open WebUIコンテナからmanaOS統合APIにアクセスする場合：
- URL: `http://host.docker.internal:9510`

### セキュリティ

- ローカル環境での使用を想定
- 本番環境では認証を追加することを推奨

---

## ✅ まとめ

- ✅ **LM Studio**: 既に接続済み、使用可能
- ⚠️ **manaOS統合API**: Open WebUIのExternal ToolsまたはFunctionsで統合可能

両方とも使える状態です！
