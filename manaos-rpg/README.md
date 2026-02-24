# ManaOS RPG Dashboard (最小で全部つながる)

registry（台帳）を読むだけで、RPGメニューUIに「ステータス/パーティ/図鑑/クエスト/ログ/マップ」を出します。

## 使い方（Windows / PowerShell）

### 1) Backend

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

#### 9510 ポート競合（起動できない）を自動で回避

`9510` がすでに LISTEN の場合、`run_backend.ps1` はリスナーのコマンドラインを確認し、
**manaos-rpg の uvicorn っぽいプロセス**なら自動で停止してから起動します。

不明なプロセスだった場合は誤爆防止のため停止せずにエラーで止まります。

強制的に kill して起動したい場合:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1 -ForceKill
```

または:

```powershell
$env:MANAOS_RPG_FORCE_KILL_PORT='1'
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

#### 操作（アクション実行）を有効化する場合

セキュリティのため、アクション実行はデフォルト無効です。

```powershell
$env:MANAOS_RPG_ENABLE_ACTIONS='1'
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

- 許可アクション定義: `registry/actions.yaml`
- クエスト一覧: `registry/quests.yaml`（`kind: action` で `action_id` を指定）

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

## 常時アクセス（常駐 + LAN）

### 常駐で起動（バックグラウンド）

backend(9510) + frontend(5173) をまとめて起動します。

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_always_on.ps1
```

LANからもアクセスしたい場合:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_always_on.ps1 -Lan
```

操作（アクション実行）も使う場合:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_always_on.ps1 -EnableActions
```

### ログオン時に自動起動（常時アクセス）

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1 -Lan
```

削除:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall_autostart.ps1
```

### LANアクセスの注意（Windows Firewall）

別端末から `http://<このPCのIP>:5173/` で開くには、Windows Firewallでポート開放が必要な場合があります。

管理者PowerShellで:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\open_firewall_ports.ps1
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

## GPU可視化（母艦の“犯人リスト”）

backendは `nvidia-smi` から以下を取得します。

- GPU: utilization / VRAM used/total / temperature / power.draw
- プロセス: pid / process_name / used_gpu_memory（取れる場合）

注意: `nvidia-smi --query-*-apps` は状況によって `used_gpu_memory` が `N/A` になり、プロセス一覧が空になります（その場合はUIに「取得なし」と出ます）。

手動確認（参考）:

```powershell
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits
nvidia-smi --query-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits
```

## 画像生成が503になる場合

ダッシュボードの画像生成は統合API（既定: `http://127.0.0.1:9502/api/comfyui/generate`）に投げます。
`comfyui_unavailable` 等で 503 の場合、だいたい ComfyUI(8188) 停止です。

- 「魔法（スキル）✨」→ ComfyUI 起動/再起動（actions有効時）
- または `start_comfyui_local.ps1` を実行

