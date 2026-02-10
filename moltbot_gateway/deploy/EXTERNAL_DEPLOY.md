# Moltbot Gateway 外部公開（貼って使える）

公開は `/moltbot/` のみ。Nginx 逆プロキシ + Basic認証 +（任意）IP制限 + HTTPS。Gateway は 127.0.0.1:8088 で待機。

**手順は `CHECKLIST_A_EXTERNAL.md` に沿って進めること。** 合格条件（ローカル 200 / 外部 200・401・429 / runner 完走＋監査増加）が全部通れば A 完了。

**B（本物 Moltbot 接続）** は `CHECKLIST_B_MOLTBOT.md` に沿って進める。executor 差し替え（EXECUTOR=moltbot）→ list_files だけ通す → execute.jsonl 確認 → file_move 解放。

## 1) systemd（Gateway 常駐）

```bash
# 雛形をコピーして編集
sudo cp deploy/moltbot-gateway.service /etc/systemd/system/
# MOLTBOT_GATEWAY_SECRET, WorkingDirectory, User, ExecStart を環境に合わせる

sudo systemctl daemon-reload
sudo systemctl enable --now moltbot-gateway
sudo systemctl status moltbot-gateway --no-pager
```

## 2) Nginx（/moltbot/ だけ公開）

- `deploy/nginx-moltbot.conf` を sites-available に配置し、`server_name` を自ドメインに変更。
- **パス二重にならない**: `proxy_pass` は末尾スラッシュなし（`http://127.0.0.1:8088`）。外から `/moltbot/health` → バックエンドへ `/moltbot/health` のまま渡る。
- `limit_req_zone` を **http ブロック**に追加: `limit_req_zone $binary_remote_addr zone=moltbot_zone:10m rate=5r/s;`

```bash
sudo ln -s /etc/nginx/sites-available/mrl-mana.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 3) Basic 認証（htpasswd）

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd mana
sudo chmod 640 /etc/nginx/.htpasswd
```

## 4) HTTPS（Certbot）

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d mrl-mana.com
```

## 5) まなOS側 .env

```env
MOLTBOT_GATEWAY_URL=https://mrl-mana.com/moltbot
MOLTBOT_GATEWAY_SECRET=REPLACE_ME
```

## 事故らない追加の守り（最低限）

1. **レート制限**: Nginx の `limit_req_zone` で `POST /moltbot/plan` を制限（上記 conf 参照）。
2. **Phase2 以降**: `allowed_domains` が無い Plan は Gateway 側で拒否（実装する場合）。
3. **Phase1**: `write_paths` が無い Plan は拒否（実装する場合）。
