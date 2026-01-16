# 🔗 Open WebUI で LM Studio に接続する方法

**作成日**: 2025-01-06

---

## ✅ 現在の状態

- ✅ Open WebUI起動済み（`http://localhost:3001`）
- ✅ LM Studioサーバー起動中（`http://127.0.0.1:1234`）
- ⚠️ 接続設定が必要（「ぜひに設定」と表示されている）

---

## 📋 LM Studio接続手順

### ステップ1: 設定画面を開く

1. Open WebUIの右上の**⚙️（設定）アイコン**をクリック
2. または、モデル名の横の**▼（ドロップダウン）**をクリック

### ステップ2: 接続を追加

1. **「Connections」**または**「接続」**タブを開く
2. **「Add Connection」**または**「接続を追加」**をクリック

### ステップ3: LM Studioの設定を入力

以下の情報を入力：

- **Connection Type（接続タイプ）**: `OpenAI Compatible` または `OpenAI`
- **Name（名前）**: `LM Studio`（任意）
- **Base URL**: `http://host.docker.internal:1234/v1`
- **API Key**: `lm-studio`（任意の文字列でOK）
- **Model（モデル）**: `qwen2.5-coder-7b-instruct`（自動検出される場合もあります）

### ステップ4: 保存してテスト

1. **「Save」**または**「保存」**をクリック
2. モデルが表示されるか確認
3. チャットでメッセージを送信して動作確認

---

## 🔧 トラブルシューティング

### 問題1: モデルが表示されない

**解決策**:
1. LM Studioのサーバーが起動しているか確認
   - LM Studioの「Server」タブで「Running」と表示されているか
2. Base URLが正しいか確認
   - `http://host.docker.internal:1234/v1` が正しいか
3. Open WebUIのログを確認
   ```powershell
   docker logs open-webui --tail 50
   ```

### 問題2: 接続エラーが発生する

**解決策**:
1. LM StudioのAPIが応答するか確認
   ```powershell
   curl http://localhost:1234/v1/models
   ```
2. Dockerコンテナからホストにアクセスできるか確認
   ```powershell
   docker exec open-webui curl http://host.docker.internal:1234/v1/models
   ```

### 問題3: 「ぜひに設定」が消えない

**解決策**:
- モデルを選択して、実際にチャットを開始すると消える場合があります
- 設定画面で接続を保存した後、ページを再読み込みしてください

---

## 📊 接続確認

### LM StudioのAPI確認

```powershell
# ホストマシンから
curl http://localhost:1234/v1/models

# Dockerコンテナから
docker exec open-webui curl http://host.docker.internal:1234/v1/models
```

### 期待される応答

```json
{
  "data": [
    {
      "id": "qwen2.5-coder-7b-instruct",
      "object": "model",
      "created": 1234567890,
      "owned_by": "lmstudio"
    }
  ]
}
```

---

## 🎉 完了後の確認事項

接続が完了すると：

- ✅ モデル選択で「qwen2.5-コーダー-7b-命令」が表示される
- ✅ チャットでメッセージを送信できる
- ✅ LM Studioのモデルが応答する

---

## 💡 補足情報

### 複数のLLMを使う場合

Open WebUIは複数のLLM接続を同時に管理できます：

- **LM Studio**: `http://host.docker.internal:1234/v1`
- **Ollama**: `http://host.docker.internal:11434`（既に設定済み）

両方のモデルがモデル選択に表示されます。

### 環境変数での自動設定

docker-compose.ymlで既に設定済み：
```yaml
environment:
  - OPENAI_API_BASE_URL=http://host.docker.internal:1234/v1
  - OPENAI_API_KEY=lm-studio
```

これにより、デフォルトでLM Studioに接続されるはずですが、UIからも設定できます。


















