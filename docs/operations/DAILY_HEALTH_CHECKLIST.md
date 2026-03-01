# Daily Health Checklist

最終更新: 2026-03-01

このチェックは「母艦の運用開始前」または「朝の定例」で実施します。
対象は以下です。
- WSL / Docker 基盤
- ManaOS 主要API（ローカル）
- CI（Validate Ledger / Workflow Policy Audit）

---

## 1) 前提

- カレントディレクトリを `manaos_integrations` にする。
- PowerShell で実行する。

```powershell
Set-Location "c:\Users\mana4\Desktop\manaos_integrations"
```

---

## 2) WSL / Docker ヘルス

### 2-1. 定期タスク登録状態

```powershell
schtasks /Query /TN "ManaOS_WSL_Docker_Health" /FO LIST
```

期待値:
- タスクが存在する
- `スケジュールされたタスクの状態: 有効`

### 2-2. 手動ヘルス実行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\check_wsl_docker_health.ps1" -Distro "Ubuntu-22.04" -Recover -TimeoutSec 120
$LASTEXITCODE
```

期待値:
- `0`
- ログに `Healthy` が出る

### 2-3. 実体確認

```powershell
wsl -l -v
docker version --format '{{.Server.Version}}'
```

期待値:
- `Ubuntu-22.04` が `Running`
- Docker Server Version が返る

---

## 3) ManaOS API ヘルス

### 3-1. Unified API 基本確認

```powershell
python -c "import requests; print(requests.get('http://127.0.0.1:9502/health',timeout=5).status_code)"
```

期待値:
- `200`

### 3-2. 読み取りAPI（readonlyキー）

```powershell
python -c "import requests; base='http://127.0.0.1:9502'; h={'X-API-Key':'ci-readonly-key'}; cands=['/api/mothership/resources','/api/file-secretary/inbox/status','/api/pixel7/resources','/api/x280/resources','/api/devices/status'];
for p in cands:
  try:
    r=requests.get(base+p,headers=h,timeout=10)
    print(p, r.status_code)
  except Exception as e:
    print(p,'ERR',e)"
```

期待値:
- 対象エンドポイントが `200`（または仕様上許可された正常コード）

---

## 4) CI ヘルス

### 4-1. Validate Ledger

```powershell
$env:GITHUB_TOKEN=$null
$env:GH_PAGER='cat'
gh run list --workflow "Validate Ledger" --limit 3 --json databaseId,displayTitle,status,conclusion,url
```

期待値:
- 最新 `completed` の `conclusion` が `success`

### 4-2. Workflow Policy Audit

```powershell
$env:GITHUB_TOKEN=$null
$env:GH_PAGER='cat'
gh run list --workflow "Workflow Policy Audit" --limit 3 --json databaseId,displayTitle,status,conclusion,url
```

期待値:
- 最新 `completed` の `conclusion` が `success`

---

## 5) 異常時の最短復旧

1. `check_wsl_docker_health.ps1 -Recover` を再実行
2. `start_vscode_cursor_services.py` を no-monitor で再起動

```powershell
$env:MANAOS_NO_MONITOR='1'
$env:MANAOS_STRICT_STARTUP='0'
python .\scripts\lifecycle\start_vscode_cursor_services.py
```

3. APIヘルス (`/health`) を再確認
4. CI失敗時は `gh run view <run_id> --log-failed` で原因取得

---

## 6) 完了判定

以下をすべて満たしたら日次チェック完了:
- WSL/Docker ヘルス `exit 0`
- Unified API `/health` が `200`
- 主要 readonly API が応答
- Validate Ledger 最新 completed が success
- Workflow Policy Audit 最新 completed が success
