# manaOS自動再起動設定ガイド
**作成日**: 2025-12-28  
**目的**: サーバーが落ちても自動で復帰する仕組み

---

## systemd設定（Linux推奨）

### 1. サービスファイルの配置

```bash
# サービスファイルをコピー
sudo cp manaos_integrations/systemd/manaos-api.service /etc/systemd/system/

# systemdをリロード
sudo systemctl daemon-reload
```

### 2. サービスを有効化・起動

```bash
# サービスを有効化（起動時に自動起動）
sudo systemctl enable manaos-api

# サービスを起動
sudo systemctl start manaos-api

# ステータス確認
sudo systemctl status manaos-api
```

### 3. ログ確認

```bash
# 最新のログを確認
sudo journalctl -u manaos-api -n 100

# リアルタイムでログを確認
sudo journalctl -u manaos-api -f
```

### 4. 再起動テスト

```bash
# サービスを停止
sudo systemctl stop manaos-api

# 自動再起動されるか確認（10秒以内に再起動される）
sudo systemctl status manaos-api
```

---

## PM2設定（Node.js環境推奨）

### 1. PM2のインストール

```bash
npm install -g pm2
```

### 2. 起動スクリプトの作成

`ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'manaos-api',
    script: 'start_server_with_notification.py',
    interpreter: 'python3',
    cwd: '/path/to/manaos_integrations',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '4G',
    env: {
      MANAOS_INTEGRATION_PORT: 9500,
      MANAOS_INTEGRATION_HOST: '0.0.0.0'
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

### 3. PM2で起動

```bash
# 設定ファイルから起動
pm2 start ecosystem.config.js

# 起動時に自動起動を有効化
pm2 startup
pm2 save

# ステータス確認
pm2 status

# ログ確認
pm2 logs manaos-api
```

---

## 起動通知の設定

### Slack通知の設定

1. `.env`ファイルにSlack Webhook URLを設定:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

2. 起動時に自動で通知が送信されます

### 通知内容

- サーバー起動完了
- 初期化完了（必須チェック5項目の状態）
- 利用可能な統合システム数

---

## 監視設定（オプション）

### ヘルスチェックの定期実行

`crontab`で5分ごとにチェック:

```bash
# crontab -e
*/5 * * * * curl -f http://localhost:9500/health || systemctl restart manaos-api
```

### Prometheus監視（オプション）

`/metrics`エンドポイントを追加して、Prometheusで監視することも可能です。

---

## トラブルシューティング

### サービスが起動しない

1. ログを確認:
   ```bash
   sudo journalctl -u manaos-api -n 50
   ```

2. ポートが使用中でないか確認:
   ```bash
   sudo netstat -tlnp | grep 9500
   ```

3. 権限を確認:
   ```bash
   ls -la /root/manaos_integrations/start_server_with_notification.py
   ```

### 自動再起動が動作しない

1. `RestartSec`を確認（10秒に設定済み）
2. ログで再起動の理由を確認
3. リソース制限（MemoryMax）を確認

---

**設定完了**: 2025-12-28













