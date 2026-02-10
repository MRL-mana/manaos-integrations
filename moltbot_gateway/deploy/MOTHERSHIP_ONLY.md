# 母艦だけでやる（このはサーバーは使わない）

Gateway も runner も 200/401/429 の確認も、**全部母艦**で完結する手順。

---

## 1. 母艦で Gateway を起動する

リポジトリルート（または `moltbot_gateway` があるところ）で:

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
$env:MOLTBOT_GATEWAY_DATA_DIR = "moltbot_gateway_data"
$env:MOLTBOT_GATEWAY_SECRET = "your_secret_here"
$env:EXECUTOR = "mock"
python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088
```

別窓で起動したままにしておく（バックグラウンドでよい）。

---

## 2. 母艦の .env をローカル向けにする

`.env` に:

```env
MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088
MOLTBOT_GATEWAY_SECRET=your_secret_here
```

（Gateway 起動時の SECRET と同じにする）

---

## 3. 母艦で runner を回す

同じ母艦の別ターミナルで:

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
python manaos_moltbot_runner.py
```

または list_files だけ:

```powershell
python manaos_moltbot_runner.py list_only
```

`moltbot_audit/YYYY-MM-DD/plan-xxx/` に 3 層監査が出ればOK。

---

## 4. 母艦で 200/401/429 を取る（ローカル用）

**localhost で Gateway を叩くだけ**なら、Nginx/Basic は使わないので:

- **200**: `curl -I http://127.0.0.1:8088/moltbot/health` の 1 行目が `HTTP/1.1 200`
- **401/429**: 母艦だけ構成では Nginx を立てないなら「スキップしてOK」。A 完了判定は「runner が最後まで通って監査が増える」で代替できる。

**母艦のドメインで外部公開する場合**（Nginx を母艦に立てる）は、従来どおり `check_external_200_401_429.ps1` で `<domain>` に母艦のドメインを入れて実行。

---

## まとめ（母艦だけ）

| やること           | 母艦でやる内容 |
|--------------------|----------------|
| Gateway 起動       | `uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088` |
| .env               | `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` + SECRET |
| runner             | `python manaos_moltbot_runner.py` または `list_only` |
| 200/401/429        | ローカルのみなら 200 だけ確認、または runner 完走で代用 |

このはサーバーは使わない。

### 一発でやる

- **Gateway だけ起動**: リポジトリルートで **`moltbot_gateway\deploy\start_gateway_mothership.bat`** を実行（別窓で 8088 が立ち上がる）。
- **Gateway 起動 ＋ list_only runner**: リポジトリルートで:

```powershell
.\moltbot_gateway\deploy\start_gateway_and_run_list_only.ps1
```

Gateway を起動して list_only runner を実行し、監査が増えるまで一発でやる。

---

## 本格運用へ

常駐化・監査ローテ・SECRET ローテ・本物接続・ロールバックは **`CHECKLIST_PRODUCTION.md`** に沿って進める。
