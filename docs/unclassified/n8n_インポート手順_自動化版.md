# n8nワークフロー インポート手順（自動化版）

**現在の状況:** n8nサーバーは起動中ですが、Web UIへの接続に問題がある可能性があります。

---

## 方法1: ブラウザで手動インポート（推奨）

### ステップ1: n8nにアクセス

```
http://100.93.120.33:5678
```

### ステップ2: ワークフローをインポート

1. **「Workflows」をクリック**
2. **「Import from File」をクリック**
3. **ファイルを選択**
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflow_template.json
   ```
4. **「Import」をクリック**

### ステップ3: ワークフローを有効化

1. **インポートしたワークフローを開く**
2. **右上の「Active」スイッチをONにする**
3. **「Save」をクリック**

---

## 方法2: API経由でインポート（APIキーが必要）

### ステップ1: n8nのAPIキーを取得

1. n8nのWeb UIにアクセス
2. **Settings** → **API** → **Create API Key**
3. APIキーをコピー

### ステップ2: 環境変数に設定

```powershell
$env:N8N_API_KEY = "your-api-key-here"
```

### ステップ3: インポートスクリプトを実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python import_n8n_workflow.py
```

---

## 方法3: このはサーバー経由でインポート

このはサーバーにSSH接続して、n8nのデータディレクトリに直接コピーする方法：

```bash
# このはサーバーに接続
ssh konoha

# n8nのワークフローディレクトリを確認
ls -la /root/.n8n/workflows/

# ワークフローファイルをコピー（必要に応じて）
# 注意: n8nのデータベース形式に合わせる必要がある場合があります
```

---

## トラブルシューティング

### n8nサーバーに接続できない場合

1. **n8nサーバーの状態を確認**
   ```powershell
   curl http://100.93.120.33:5678/healthz
   ```

2. **このはサーバーでn8nを再起動**
   ```bash
   ssh konoha
   sudo systemctl restart n8n
   ```

3. **ファイアウォールの設定を確認**
   - ポート5678が開いているか確認

### APIキーが取得できない場合

- n8nのバージョンによっては、APIキー機能が無効になっている場合があります
- その場合は、方法1（ブラウザで手動インポート）を使用してください

---

## インポート後の確認

### 1. ワークフローがインポートされたか確認

- n8nのWeb UIで「Workflows」を確認
- 「ManaOS Image Generation Workflow」が表示されているか確認

### 2. ワークフローが有効化されているか確認

- ワークフローを開いて、右上の「Active」スイッチがONになっているか確認

### 3. Webhook URLを確認

- ワークフローを開いて、「Webhook」ノードを確認
- Webhook URLをコピー（例: `http://100.93.120.33:5678/webhook/comfyui-generated`）

### 4. 環境変数を設定

```powershell
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
```

---

## 次のステップ

インポートが完了したら：

1. ✅ ワークフローが有効化されているか確認
2. ✅ Webhook URLを環境変数に設定
3. ✅ 完全自動化ループをテスト

---

**進捗:** 98% → **100%まであと2%**


















