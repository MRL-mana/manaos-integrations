# A：このはで外部公開（ドメイン経由）事故らないチェックリスト

前提：`moltbot_gateway/deploy/` に `moltbot-gateway.service` / `nginx-moltbot.conf` / `EXTERNAL_DEPLOY.md` が揃っている状態。

---

## ✅ 0. 先に確認すること（1分）

- [ ] ドメイン（例：`mrl-mana.com`）がこのはの IP に向いている（A レコード）
- [ ] 80/443 が開いている（このは FW / UFW / セキュリティグループ）
- [ ] Gateway は **127.0.0.1:8088** で待つ設計（外に直接晒さない）

> ここがズレると後の作業が全部“沼”になる。最初に釘。

---

## ✅ 1. Gateway（systemd）を入れる

### 1-1. venv と依存（初回だけ）

- [ ] `moltbot_gateway/.venv` を作る
- [ ] `fastapi uvicorn pydantic` が入っている

```bash
cd ~/moltbot_gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn pydantic
```

### 1-2. systemd 設置

- [ ] `deploy/moltbot-gateway.service` を `/etc/systemd/system/` にコピー
- [ ] **SECRET / WorkingDirectory / ExecStart のパス**を現環境に合わせて書き換え
- [ ] `MOLTBOT_GATEWAY_SECRET` を service 直書き or `EnvironmentFile` で注入（おすすめは EnvironmentFile）

#### おすすめ：EnvironmentFile 運用（SECRET を service に直書きしない）

- [ ] `/etc/moltbot-gateway.env` を作る（権限 600）

```bash
sudo bash -c 'cat > /etc/moltbot-gateway.env <<EOF
MOLTBOT_GATEWAY_SECRET=REPLACE_ME
MOLTBOT_GATEWAY_DATA_DIR=/var/lib/moltbot_gateway
EOF'
sudo chmod 600 /etc/moltbot-gateway.env
```

service 側は `EnvironmentFile=/etc/moltbot-gateway.env` を使う（個別 Environment 行は削除してよい）。
雛形は `deploy/moltbot-gateway.service` の「EnvironmentFile 版」コメントを参照。

反映：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now moltbot-gateway
sudo systemctl status moltbot-gateway --no-pager
```

### 1-3. ローカル死活確認（重要）

- [ ] `curl http://127.0.0.1:8088/moltbot/health` が 200

```bash
curl -i http://127.0.0.1:8088/moltbot/health
```

---

## ✅ 2. Nginx（/moltbot/ だけ公開＋Basic＋レート制限）

### 2-1. Nginx インストール

- [ ] Nginx が入っている

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### 2-2. rate limit zone（http ブロック）を有効化

- [ ] `/etc/nginx/nginx.conf` の **http {}** 内に zone を定義

例（`http {` の直下などに追加）：

```nginx
limit_req_zone $binary_remote_addr zone=moltbot_zone:10m rate=5r/s;
```

### 2-3. サイト設定に `nginx-moltbot.conf` を配置

- [ ] `deploy/nginx-moltbot.conf` を sites-available に配置
- [ ] `server_name` / upstream(127.0.0.1:8088) を確認
- [ ] location が `/moltbot/` のみ
- [ ] Basic 認証が有効

反映：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 2-4. Basic 認証（htpasswd）

- [ ] `apache2-utils` を入れる
- [ ] `/etc/nginx/.htpasswd` を作る（権限 640）

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd mana
sudo chmod 640 /etc/nginx/.htpasswd
```

### 2-5. 外から疎通（HTTP 段階）

- [ ] ブラウザで `http://<domain>/moltbot/health` が **二重パス**（`/moltbot/moltbot/health`）になっていないか確認
- [ ] `curl -u` で 200 が返る

```bash
curl -u mana 'http://mrl-mana.com/moltbot/health'
```

> パスが二重になったら `proxy_pass` の末尾スラッシュが原因。`nginx-moltbot.conf` は「パス二重にならない」設定にしてあるので、そのまま使うこと。

---

## ✅ 3. HTTPS（Certbot）で“外から本番”にする

- [ ] certbot を入れる
- [ ] nginx プラグインで証明書取得
- [ ] 80→443 リダイレクト確認

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d mrl-mana.com
```

確認：

- [ ] `curl -I https://mrl-mana.com/moltbot/health -u mana` が 200

---

## ✅ 4. “事故らない守り”の実装チェック（EXTERNAL_DEPLOY.md の 3 点）

### 4-1. レート制限（Nginx）

- [ ] `/moltbot/` location に `limit_req zone=moltbot_zone burst=... nodelay;` がある
- [ ] （任意）ログで 429 が出ることを確認（短時間に連打して試す）

### 4-2. allowed_domains が無い Plan は拒否（Phase2 以降の前提）

- [ ] Gateway で plan 受理時にチェック（scope が web 系なら必須）。Phase1 だけなら「将来のガードとして残す」で OK

### 4-3. write_paths が無い Plan は拒否（Phase1 でも推奨）

- [ ] `constraints.write_paths` が無い plan は 400 で落とす（実装する場合）
- [ ] runner の Phase1 は `phase1_safe()` で入っているので、落ちないはず

---

## ✅ 5. まなOS側を本番 URL に切り替え

- [ ] `.env` を HTTPS + /moltbot に変更
- [ ] secret 一致

例：

```env
MOLTBOT_GATEWAY_URL=https://mrl-mana.com/moltbot
MOLTBOT_GATEWAY_SECRET=REPLACE_ME
```

そして：

- [ ] `python manaos_moltbot_runner.py` を実行して、監査が増える

---

## トラブルが起きやすい TOP3（先に潰す）

1. **proxy_pass の末尾スラッシュ**でパスが二重 → 末尾スラッシュを付けない（`nginx-moltbot.conf` 済み）
2. **limit_req_zone を http {} に書いていない**（`nginx -t` で落ちる）
3. **systemd の ExecStart パス**がズレて起動していない（`status` で即バレ）

---

## 運用で“絶対やる”2 つ（地味だけど効く）

- [ ] `/var/log/nginx/access.log` と gateway のログを「監査と同じ日付」で追えるようにする
- [ ] `moltbot_gateway` の SECRET は **定期ローテ**（漏れていなくても年 1 で OK）

---

# A 完成の“合格条件”（全部通れば外部公開完了）

## ✅ 1) ローカル（このは内）確認

- [ ] `curl -i http://127.0.0.1:8088/moltbot/health` → **200**
- [ ] `systemctl status moltbot-gateway` → **active (running)**

## ✅ 2) 外部（インターネット側）確認 — 200 / 401 / 429 が揃えば合格（最短）

ドメインとユーザーだけ置換して実行。

**1) 200（監視用 health・認証なし）**

```bash
curl -I https://<domain>/moltbot/health
```

期待: `HTTP/2 200` または `HTTP/1.1 200`

**2) 401（/moltbot/ は認証必須）**

```bash
curl -I https://<domain>/moltbot/ -s -o /dev/null -w "%{http_code}\n"
```

期待: `401`

**3) 429（レート制限確認・短時間に連打）**

```bash
for i in {1..30}; do
  curl -s -o /dev/null -u <user>:<pass> -w "%{http_code}\n" https://<domain>/moltbot/
done | sort | uniq -c
```

期待: `429` が混ざる（出たら勝ち）

## ✅ 3) まなOS runner で実運用確認

- [ ] `.env` を `https://<domain>/moltbot` に切り替え済み
- [ ] `python manaos_moltbot_runner.py` が最後まで完走
- [ ] `moltbot_audit/YYYY-MM-DD/plan-xxx/` に 3 層監査一式が増える

> **A 完了判定**: 外部疎通の結果を **数字だけ**（200 / 401 / 429）貼れば OK。揃ったら A 完了宣言して、次は executor 差し替え（本物接続）パッチへ。
> **取り方** → `HOW_TO_GET_200_401_429.md`。**一発で取る** → 母艦で `check_external_200_401_429.ps1` または `check_external_200_401_429.sh` を実行（ドメイン・ユーザー・パスを渡す）。

---

# 仕上げの最終チェック（A 完了後にやると安心な 2 つ）

## ✅ 1) Nginx の設定が意図通りか（優先順位の確認）

- [ ] `/moltbot/health` が auth なしで 200
- [ ] `/moltbot/` は auth ありで 401/200
- [ ] `/moltbot` は 301 で `/moltbot/`

```bash
curl -I https://<domain>/moltbot | head -n 1
curl -I https://<domain>/moltbot/health | head -n 1
curl -I https://<domain>/moltbot/ | head -n 1
```

## ✅ 2) 監査とアクセスログの相関が取れているか

1 回だけ runner を回して:

- [ ] `moltbot_audit/.../plan-xxx/` が出る
- [ ] `/var/log/nginx/moltbot_access.log` に同じ `plan_id="plan-xxx"` が残る（Nginx で `log_format moltbot` と `access_log ... moltbot` を有効にした場合）

---

# 補足：Gateway の health パス

Gateway 側は **`GET /moltbot/health`** で実装済み。Nginx の `location = /moltbot/health` と一致している。ズレた場合は Nginx 側の location を合わせる。

---

# 次（B）への助走：executor 差し替えの方針

A 完了後は **Gateway executor 差し替え**。いきなり本物で全部やらず、順番に:

1. `EXECUTOR=mock`（現状）
2. `EXECUTOR=moltbot` に切替
3. 最初は `list_files` だけ通す
4. `execute.jsonl` のイベントが流れることを確認
5. その後 file_move 等を解放

**B の骨格はすでに置いてある**（`executor/mock.py` と `executor/moltbot.py`、`gateway_app` は `executor.run(plan)` に置換済み）。数字が揃ったら本物接続を `moltbot.py` に差し替えるだけ。

---

# 外部疎通でよくある“詰まり”と即対応

数字が期待通り出ないときの切り分け:

| 現象 | 原因の目安 | 対応 |
|------|------------|------|
| **200 が出ない** | DNS / Firewall / Certbot / `server_name` のどれか | A レコード・80/443・証明書・server_name を確認 |
| **401 にならない（200 になる）** | `/moltbot/` に auth が効いていない（location の優先順位） | `location = /moltbot/health` が先で auth なし、`location /moltbot/` で auth ありになっているか確認 |
| **429 が出ない** | `limit_req_zone` が http{} に無い or rate/burst が緩い | http ブロックに zone 定義、rate を 5r/s 等に |
| **429 しか出ない** | rate が厳しすぎ or burst が小さすぎ | burst を少し上げる or rate を緩める |

---

# パス二重を完全に潰すための補強（任意・運用耐性アップ）

今の設定で正しい。さらに強くするなら以下 2 つ。

## 1) `/moltbot`（末尾スラッシュなし）を `/moltbot/` へリダイレクト

- [ ] `location = /moltbot { return 301 /moltbot/; }` を追加（`nginx-moltbot.conf` の補強オプション参照）

## 2) health だけ認証なし（監視用）

- [ ] `location = /moltbot/health { ... }` を Basic なしで先に書く（監視を入れる場合）。`nginx-moltbot.conf` の補強オプション参照。

---

# 事故らない守り 3 点を“実装で強制”する場合（Gateway 側）

まなOSがバグっても外で止まるようにする。

- [ ] **write_paths 未指定は拒否（Phase1 でも必須）**: `constraints.write_paths` が空 or None → 400
- [ ] **allowed_domains 未指定は拒否（web 系 scope のみ）**: scope が browser/web のときだけ必須。Phase1(file_organize) は対象外で OK
- [ ] **max_actions 未指定は拒否**: `constraints.max_actions` が無い → 400（Phase1_safe で入るので runner は落ちない）

実装例は `gateway_app.py` の `_validate_plan_constraints()` を参照。

---

# 公開後“運用で必ずやる 2 つ”を実戦向けに

## 1) ログの相関（nginx ↔ plan_id）を確実にする

- [ ] まなOS側で `POST /moltbot/plan` に **X-Plan-Id** ヘッダを付ける（plan_id をそのまま）
- [ ] Nginx の **log_format** に `plan_id="$http_x_plan_id"` を入れる
- [ ] `/moltbot/` の **access_log** を `moltbot_access.log` に分ける（フォーマットは `moltbot`）

→ 監査ディレクトリと 1:1 で追える。事故調査・テンプレ化に効く。`nginx-moltbot.conf` のログフォーマット例参照。

## 2) SECRET ローテ後に“署名失敗アラート”を出す（将来）

- [ ] Gateway が `401 Invalid signature` を返した回数を数えて Slack 通知、など（後ででよい。今はメモのみ）
