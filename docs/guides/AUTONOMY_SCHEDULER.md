# 自律システム 定期実行（スケジューラ）

Runbook と自律タスクを定期的に走らせるには、**Autonomy System** の `POST /api/execute` を一定間隔で呼びます。

## 前提

- **Autonomy System** が起動していること（既定: `http://localhost:5124`）
- レベル L4 以上で Runbook が due になると実行される

## 1. 1回だけ実行（手動・テスト）

```powershell
cd manaos_integrations
.\scripts\autonomy_execute_once.ps1
```

環境変数で先を変える場合:

```powershell
$env:AUTONOMY_URL = "http://localhost:5124"
.\scripts\autonomy_execute_once.ps1
```

## 2. 一定間隔で繰り返し（PowerShell でループ）

```powershell
.\scripts\schedule_autonomy_execute.ps1 -IntervalMinutes 10
```

- 10分ごとに `POST /api/execute` を実行。停止は **Ctrl+C**。
- 間隔を変える: `-IntervalMinutes 15`

## 3. Windows タスクスケジューラで登録

1. **タスクスケジューラ** を開く。
2. **基本タスクの作成** → 名前例: `ManaOS Autonomy Execute`
3. **トリガー**: 毎日、または「10分ごと」など（繰り返し間隔で設定）。
4. **操作**: プログラムの開始
   - プログラム: `powershell.exe`
   - 引数例: `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\<user>\Desktop\manaos_integrations\scripts\autonomy_execute_once.ps1"`
5. **開始**: `manaos_integrations` のフルパスを「開始する場所」に指定するとよい。

「10分ごと」にする場合は、トリガーで「1回だけ」ではなく「タスクの繰り返し間隔: 10分」を指定するか、上記の `schedule_autonomy_execute.ps1` を「1回だけ」起動するタスクにし、スクリプト側でループさせる方法があります。

## 4. n8n で定期実行

1. **Schedule Trigger** ノード: Cron で `*/10 * * * *`（10分ごと）などに設定。
2. **HTTP Request** ノード:
   - Method: POST
   - URL: `http://localhost:5124/api/execute`
   - Body: 空でよい（JSON なしで OK な実装とする）
3. 必要なら **IF** で status や `runbook_count` を見て通知ノードへ分岐。

## 5. 確認

- レベル・予算・Runbook 最終実行: `GET http://localhost:5124/api/dashboard`
- 実行結果の詳細: `POST /api/execute` のレスポンスの `runbook_results` / `results`
