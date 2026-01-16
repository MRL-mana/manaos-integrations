# 緊急操作パネル デプロイメントガイド

## デプロイ手順

### Step 1: ファイルの配置確認

母艦で以下を確認：

```bash
# templatesディレクトリの確認
ls -la /root/templates/emergency_panel.html
# または
ls -la /root/OneDrive/Desktop/templates/emergency_panel.html

# unified_api_server.pyの確認
ls -la /root/manaos_integrations/unified_api_server.py
```

### Step 2: サーバーの再起動

#### systemdサービスとして実行されている場合

```bash
# サービスを再起動
sudo systemctl restart manaos-api

# 状態確認
sudo systemctl status manaos-api

# ログ確認
sudo journalctl -u manaos-api -n 50
```

#### 直接実行している場合

```bash
# 既存のサーバープロセスを停止
pkill -f unified_api_server.py

# サーバーを起動
cd /root/manaos_integrations
python unified_api_server.py
```

### Step 3: 動作確認

#### ローカルで確認

```bash
# ヘルスチェック
curl http://localhost:9500/health

# 緊急パネルHTML確認
curl http://localhost:9500/emergency

# 緊急ステータスAPI確認
curl http://localhost:9500/api/emergency/status
```

#### リモートから確認（Tailscale経由）

X280のPowerShellで：

```powershell
# テストスクリプトを実行
cd C:\Users\mana\OneDrive\Desktop\x280_setup
.\setup_emergency_panel.ps1
```

### Step 4: エラーの場合

#### /emergency が404を返す場合

1. **ファイルのパスを確認**
   ```bash
   # unified_api_server.pyの場所を確認
   python -c "from pathlib import Path; import sys; sys.path.insert(0, '/root/manaos_integrations'); from unified_api_server import *; print(Path(__file__).parent.parent / 'templates')"
   ```

2. **ログを確認**
   ```bash
   # systemdの場合
   sudo journalctl -u manaos-api -n 100 | grep emergency
   
   # 直接実行の場合
   # サーバーのコンソール出力を確認
   ```

3. **手動でHTMLを読み込むテスト**
   ```python
   from pathlib import Path
   template_dir = Path('/root/manaos_integrations').parent / "templates"
   html_file = template_dir / "emergency_panel.html"
   print(f"Template dir: {template_dir}")
   print(f"HTML file exists: {html_file.exists()}")
   ```

#### /api/emergency/status がエラーを返す場合

1. **システムコマンドの権限確認**
   ```bash
   # systemctlコマンドが実行できるか確認
   systemctl is-active n8n
   
   # tailコマンドが実行できるか確認
   tail -n 10 /var/log/syslog
   ```

2. **ログファイルのパス確認**
   ```bash
   # ログファイルが存在するか確認
   ls -la /root/.n8n/logs/n8n.log
   ls -la /root/logs/error.log
   ls -la /root/logs/command-hub.log
   ls -la /root/logs/daily.log
   ```

---

## 自動起動設定

### systemdサービスとして設定

`/etc/systemd/system/manaos-api.service`:

```ini
[Unit]
Description=ManaOS統合APIサーバー
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/manaos_integrations
Environment="MANAOS_INTEGRATION_PORT=9500"
Environment="MANAOS_INTEGRATION_HOST=0.0.0.0"
ExecStart=/usr/bin/python3 /root/manaos_integrations/unified_api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

サービスの有効化：

```bash
sudo systemctl daemon-reload
sudo systemctl enable manaos-api
sudo systemctl start manaos-api
```

---

## トラブルシューティング

### ポートが既に使用されている

```bash
# ポート9500を使用しているプロセスを確認
sudo lsof -i :9500
# または
sudo netstat -tlnp | grep 9500

# プロセスを停止
sudo kill <PID>
```

### ファイルが見つからない

```bash
# ファイルの検索
find /root -name "emergency_panel.html" -type f

# パスの確認
python -c "from pathlib import Path; print(Path('/root/manaos_integrations/unified_api_server.py').parent.parent / 'templates')"
```

### 権限エラー

```bash
# ファイルの権限確認
ls -la /root/templates/emergency_panel.html

# 必要に応じて権限を変更
chmod 644 /root/templates/emergency_panel.html
```

---

## 確認コマンド（まとめ）

```bash
# サーバー状態確認
curl http://localhost:9500/health

# 緊急パネル確認
curl -I http://localhost:9500/emergency

# 緊急ステータス確認
curl http://localhost:9500/api/emergency/status | jq

# ログ確認
sudo journalctl -u manaos-api -n 50 -f
```



