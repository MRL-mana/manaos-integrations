# ManaOS 外部Watchdog（Raspberry Pi / LAN内常駐・MVP）

目的（D優先）:
- `ping OK` なのに `:9502/ready` が `200` を返さない状態が一定時間続いたら **OSフリーズ疑い** として復旧を実行
- **復旧アクションを必ず打てる**（電断→復帰）ことをSLOの核にする
- 結果（成功/失敗）を **Slackに必ず返す**

## 前提
- 監視筐体（Raspberry Pi）が **家LAN内で常時稼働**
- スマートプラグ（Tapo P110/P105系）の制御は **当面クラウドでもOK**
  - 推奨: n8n 側でTapoの電断復帰を実行（watchdogはWebhookで命令するだけ）

## 監視対象
- L1: `http://<MOTHER_IP>:9502/ready`
  - ここは「listenできていれば200」の軽量判定（誤検知電断を減らす）
- 深い状態は `http://<MOTHER_IP>:9502/status` を人間が見る（後で `/core` を追加する想定）

## n8n 側（Power Cycle Webhook）
watchdogは `POWER_CYCLE_WEBHOOK_URL` にPOSTします。

期待I/F:
- `POST` JSON: `{ "action": "power_cycle", "off_seconds": 15, "reason": "...", "incident_id": "..." }`
- 成功: 2xx を返す

n8n の実装は最短でOK:
- Webhook Trigger（受信）
- （Tapo連携）OFF → wait → ON
- 念のため、n8nからもSlackへログを投げても良い（ただしwatchdogのSlack通知が正本）

## Slack
- watchdogが `SLACK_WEBHOOK_URL` に直接投げます（n8nが落ちても通知が死なない）

## 起動
例（Pi）:
- `export MANAOS_HOST=192.168.1.10`
- `export POWER_CYCLE_WEBHOOK_URL=https://<n8n-host>/webhook/manaos-powercycle`
- `export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`
- `python3 watchdog.py`

## 推奨パラメータ（MVP）
- `CHECK_INTERVAL_SEC=10`
- `SUSPECT_WINDOW_SEC=60`
- `COOLDOWN_SEC=180`
- `BOOT_WAIT_MAX_SEC=300`
- `MAX_HARD_RETRIES=2`

## ステート
- `watchdog_state.json` に保存（再起動しても電断ループしにくい）
