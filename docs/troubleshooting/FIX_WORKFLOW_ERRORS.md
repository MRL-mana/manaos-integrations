# 🔧 ワークフローエラー修正ガイド

## 🎯 現在の状況

ワークフローはインポートされていますが、以下のエラーがあります：

1. **Slack通知ノード**: 認証情報が必要（赤い警告アイコン）
2. **Obsidian保存ノード**: 設定が必要（疑問符アイコン）

---

## ✅ 修正方法

### 方法A: 現在のワークフローを修正（推奨）

n8n UIで直接修正：

#### 1. Slack通知ノードを修正

1. **「Slack通知」ノードをクリック**
2. **ノード設定を開く**
3. **認証方法を変更**:
   - **「Slack」ノードの代わりに「HTTP Request」ノードを使用**
   - または、**Slack認証情報を設定**

**推奨: HTTP Requestノードに変更**

1. **「Slack通知」ノードを削除**
2. **「HTTP Request」ノードを追加**
3. **設定**:
   - **URL**: `={{ $env.SLACK_WEBHOOK_URL }}`
   - **Method**: POST
   - **Body**: JSON
   - **JSON Body**: `{{ { "text": $json.message } }}`

#### 2. Obsidian保存ノードを修正

1. **「Obsidian保存」ノードをクリック**
2. **ノード設定を開く**
3. **ファイルパスを設定**:
   - **File Name**: `browse_ai_log.md`
   - **File Content**: `={{ $json.timestamp + ": " + $json.message }}`
   - **Operation**: Append

---

### 方法B: シンプル版ワークフローをインポート

**新しいファイル**: `browse_ai_manaos_integration_simple.json`

このファイルは：
- Slack通知をHTTP Requestノードに変更（認証不要）
- ManaOS判断APIノードを削除（シンプル化）
- より確実に動作する構造

---

## 🚀 シンプル版ワークフローのインポート

1. **現在のワークフローを削除**（必要に応じて）
2. **「Import from File」をクリック**
3. **ファイルを選択**:
   ```
   browse_ai_manaos_integration_simple.json
   ```
4. **インポート完了**

---

## 📋 シンプル版ワークフローの構成

1. **Browse AI Webhook** - Webhook受信
2. **データ整形・重要度判定** - データ処理
3. **通知判定** - IF条件
4. **Slack通知** - HTTP Request（Webhook URL使用）
5. **Obsidian保存** - ファイル書き込み

**削除したノード**:
- ManaOS判断API（後で追加可能）

---

## 🎯 次のステップ

ワークフロー修正後:

1. **環境変数設定**:
   ```powershell
   $env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
   ```

2. **ワークフローを有効化**（トグルスイッチをON）

3. **テスト実行**

---

## 💡 トラブルシューティング

### Slack通知が動作しない場合

1. **環境変数確認**: `$env:SLACK_WEBHOOK_URL`
2. **HTTP RequestノードのURL確認**: Webhook URLが正しいか
3. **テスト実行**: ワークフローを手動実行して確認

### Obsidian保存が動作しない場合

1. **ファイルパス確認**: 書き込み権限があるか
2. **ファイル名確認**: 正しいパスが設定されているか

---

## 📚 関連ファイル

- `browse_ai_manaos_integration_simple.json` - シンプル版ワークフロー
- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド

---

**現在のワークフローを修正するか、シンプル版をインポートしてください！**🔥



