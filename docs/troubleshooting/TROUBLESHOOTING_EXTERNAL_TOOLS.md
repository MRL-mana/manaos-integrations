# 🔧 External Tools トラブルシューティング

**問題**: LLMがmanaOS統合APIを呼び出さない

---

## 🔍 確認事項

### 1. External Toolsの設定確認

1. **設定画面を開く**
   - 右上の⚙️アイコンをクリック
   - 「External Tools」タブを選択

2. **接続が追加されているか確認**
   - 一覧に「manaOS統合API」またはURL `http://host.docker.internal:9502` が表示されているか

3. **設定内容を確認**
   - URL: `http://host.docker.internal:9502`
   - OpenAPI Spec: **OFF**（白）
   - 認証: 空白でOK

---

## 🔧 解決方法

### 方法1: Functionsとして設定する（推奨）

External Toolsではなく、**Functions**として設定すると、より確実に動作します。

1. **設定画面を開く**
   - 右上の⚙️アイコンをクリック
   - 左サイドバーで「**Functions**」を選択

2. **関数を追加**
   - 「Add Function」をクリック
   - 以下の情報を入力：

**画像生成（ComfyUI）**
```
Name: generate_image_comfyui
Description: ComfyUIを使って画像を生成します。プロンプトを指定してください。
URL: http://host.docker.internal:9502/api/comfyui/generate
Method: POST
Parameters:
{
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "description": "画像生成のプロンプト"
    }
  },
  "required": ["prompt"]
}
```

3. **保存**
   - 「Save」をクリック

4. **チャットで使用**
   - チャット画面に戻る
   - 「ComfyUIで画像を生成して、美しい風景を描いて」と入力
   - LLMが自動的にFunctionsを呼び出す

---

### 方法2: システムプロンプトに指示を追加

1. **設定画面を開く**
   - 右上の⚙️アイコンをクリック
   - 「一般」タブを選択

2. **システムプロンプトを編集**
   - 「システムプロンプトをここに入力」に以下を追加：

```
画像生成が必要な場合は、generate_image_comfyui関数を使用してください。
ファイルアップロードが必要な場合は、upload_to_google_drive関数を使用してください。
Obsidianノート作成が必要な場合は、create_obsidian_note関数を使用してください。
```

3. **保存**
   - 「保存」をクリック

---

### 方法3: 直接APIを呼び出す

チャットで以下のように明示的に指示：

```
generate_image_comfyui関数を使って、プロンプト「美しい風景」で画像を生成してください
```

---

## 📋 確認コマンド

### manaOS統合APIの動作確認

```powershell
# 画像生成APIの確認
curl http://127.0.0.1:9502/api/comfyui/generate -X POST -H "Content-Type: application/json" -d '{\"prompt\":\"test\"}'
```

### Open WebUIのログ確認

```powershell
docker logs open-webui --tail 50
```

---

## 💡 推奨される設定

**Functions**として設定することを推奨します：
- External Toolsよりも確実に動作する
- LLMが自動的にFunctionsを認識して呼び出す
- パラメータの型定義が明確

---

**まずは「Functions」タブで設定してみてください！**
