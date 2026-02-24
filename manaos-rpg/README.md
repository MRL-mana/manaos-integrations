# ManaOS RPG Dashboard (最小で全部つながる)

registry（台帳）を読むだけで、RPGメニューUIに「ステータス/パーティ/図鑑/クエスト/ログ/マップ」を出します。

## 使い方（Windows / PowerShell）

### 1) Backend

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

確認:

- http://localhost:9510/health
- http://localhost:9510/api/snapshot

### 2) Frontend

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_frontend.ps1
```

確認:

- http://localhost:5173/

### 3) 自動更新（任意）

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_snapshot_loop.ps1 -IntervalSec 15
```

## 台帳の編集

- registry/services.yaml
- registry/models.yaml
- registry/features.yaml
- registry/devices.yaml
- registry/quests.yaml

## services.yaml の生存判定

- `port`: ポート疎通
- `health_url`: HTTP 200-299 なら生存
- `kind: docker` + `container`: `docker ps` で起動確認（+ポート/healthも加点）

### PM2（Node常駐）

`pm2 jlist` から `status / restart_time / pm_uptime` を取ります。

```yaml
- id: tool_server_pm2
	name: tool-server
	kind: pm2
	pm2_name: tool-server
	port: 9502
	health_url: http://127.0.0.1:9502/health
	tags: [core, always_on]
	depends_on: []
```

UI表示:

- `pm2_status`（online/stopped/errored）
- `restart_count`（PM2のrestart_time）

