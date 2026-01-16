# ⚡ すぐに使える方法：システムプロンプトで設定

**OpenAPI仕様の追加には時間がかかるため、まずはこの方法で試してください！**

---

## 🚀 設定手順

### ステップ1: Open WebUIの設定を開く

1. `http://localhost:3001` にアクセス
2. 右上の⚙️（設定）アイコンをクリック
3. 「**一般**」タブが選択されていることを確認

### ステップ2: システムプロンプトを編集

「システムプロンプトをここに入力」に以下をコピー&ペースト：

```
画像生成が必要な場合は、以下のAPIを呼び出してください：
POST http://host.docker.internal:9500/api/comfyui/generate
Content-Type: application/json
Body: {"prompt": "画像生成のプロンプト", "width": 512, "height": 512, "steps": 20}

ファイルをGoogle Driveにアップロードする必要がある場合は：
POST http://host.docker.internal:9500/api/google_drive/upload
Content-Type: application/json
Body: {"file_path": "ファイルパス"}

Obsidianにノートを作成する必要がある場合は：
POST http://host.docker.internal:9500/api/obsidian/create
Content-Type: application/json
Body: {"title": "ノートタイトル", "content": "ノート内容", "tags": ["タグ1", "タグ2"]}

CivitAIでモデルを検索する必要がある場合は：
GET http://host.docker.internal:9500/api/civitai/search?query=検索クエリ&limit=10
```

### ステップ3: 保存

右下の「**保存**」ボタンをクリック

### ステップ4: チャットで使用

1. チャット画面に戻る
2. モデルを選択（LM StudioまたはOllama）
3. 以下のようなメッセージを入力：

   - 「ComfyUIで画像を生成して、美しい風景を描いて」
   - 「Google Driveにファイルをアップロードして」
   - 「Obsidianにノートを作成して、タイトルは「今日のメモ」、内容は「テスト」で」

---

## ✅ これで使えます！

システムプロンプトに指示を追加することで、LLMがmanaOS統合APIを呼び出すようになります。

---

## 🔧 OpenAPI仕様を追加する方法（オプション）

もしOpenAPI仕様を追加したい場合は、コンテナを再ビルドする必要があります：

```powershell
docker-compose -f docker-compose.manaos-services.yml build unified-api
docker-compose -f docker-compose.manaos-services.yml up -d unified-api
```

ただし、システムプロンプトの方法でも十分に動作します！
