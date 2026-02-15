# 🚀 manaOS統合 クイックスタートガイド

**作成日**: 2025-01-06

---

## ✅ 現在の状態

### 起動中のサービス

- ✅ **Open WebUI**: `http://127.0.0.1:3001`（起動中）
- ✅ **manaOS統合API**: `http://127.0.0.1:9502`（起動中）
- ✅ **LM Studio**: `http://127.0.0.1:1234`（起動中、モデル利用可能）

---

## 🎯 すぐに使える機能

### 1. LM Studio（既に接続済み）

Open WebUIのチャット画面で：
1. モデル選択で「qwen2.5-coder-7b-instruct」または「qwen2.5-coder-14b-instruct」を選択
2. チャットを開始

✅ **既に使えます！**

---

### 2. manaOS統合API（Functions設定が必要）

#### 設定方法

1. **設定画面を開く**
   - 右上の⚙️アイコンをクリック
   - 左サイドバーで「**Functions**」を選択

2. **関数を追加**
   - 「Add Function」をクリック
   - 以下の情報を入力：

**画像生成（ComfyUI）**
```
Name: generate_image_comfyui
Description: ComfyUIを使って画像を生成します
URL: http://host.docker.internal:9502/api/comfyui/generate
Method: POST
```

**Google Driveアップロード**
```
Name: upload_to_google_drive
Description: ファイルをGoogle Driveにアップロードします
URL: http://host.docker.internal:9502/api/google_drive/upload
Method: POST
```

**Obsidianノート作成**
```
Name: create_obsidian_note
Description: Obsidianにノートを作成します
URL: http://host.docker.internal:9502/api/obsidian/create
Method: POST
```

3. **保存してチャットで使用**
   - 設定を保存
   - チャット画面に戻る
   - 「ComfyUIで画像を生成して」などと入力すると、自動的にmanaOS統合APIが呼び出されます

---

## 📋 利用可能なmanaOS統合API機能

### 画像生成
- **エンドポイント**: `/api/comfyui/generate`
- **用途**: ComfyUIを使って画像を生成

### ファイル管理
- **エンドポイント**: `/api/google_drive/upload`
- **用途**: Google Driveにファイルをアップロード

### ノート作成
- **エンドポイント**: `/api/obsidian/create`
- **用途**: Obsidianにノートを作成

### モデル検索
- **エンドポイント**: `/api/civitai/search`
- **用途**: CivitAIでモデルを検索

---

## 🔍 動作確認

### LM Studioの確認
```powershell
curl http://127.0.0.1:1234/v1/models
```

### manaOS統合APIの確認
```powershell
curl http://127.0.0.1:9502/status
```

---

## 💡 使い方の例

### LM Studioでチャット
1. Open WebUIのチャット画面を開く
2. モデル選択で「qwen2.5-coder-7b-instruct」を選択
3. メッセージを入力して送信

### manaOS統合APIで画像生成
1. Functions設定を完了（上記参照）
2. チャット画面で「ComfyUIで画像を生成して、美しい風景を描いて」と入力
3. 自動的にmanaOS統合APIが呼び出され、画像が生成されます

---

## 🎉 まとめ

- ✅ **LM Studio**: 既に接続済み、すぐ使えます
- ⚠️ **manaOS統合API**: Functions設定で使用可能

両方とも使える状態です！

---

**詳細な設定手順**: `OPENWEBUI_MANAOS_SETUP_COMPLETE.md` を参照してください。
