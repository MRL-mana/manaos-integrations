# Open WebUI × ManaOS ツール受け入れチェックリスト

## 目的

Open WebUI から ManaOS Tool Server の 5 ツール（`service_status`, `check_errors`, `generate_image`, `vscode_open_file`, `execute_command`）が実運用で使えることを確認する。

## 前提

- `start_openwebui_manaos_full.ps1` で必須サービスを起動済み
- Open WebUI が `http://127.0.0.1:3001` で利用可能
- Tool Server が `http://127.0.0.1:9503` で利用可能

## 自動チェック

以下を実行して、起動状態と API 疎通を確認する。

```powershell
powershell -ExecutionPolicy Bypass -File .\run_openwebui_tool_acceptance.ps1
```

期待結果:

- `[OK]` が主要チェック（サービス、OpenAPI、統合テスト）で表示される
- `logs/tool_server_security.log` が作成/更新される

## 手動受け入れ（Open WebUI チャット）

### ケース 1: ツール呼び出しの基本

入力例:

```text
今のManaOSサービス状態を確認して、止まっているものがあれば名前だけ教えて
```

期待結果:

- `service_status` が呼び出される
- 応答にサービス稼働情報が含まれる

### ケース 2: VS Code ファイル操作

入力例:

```text
C:/Users/mana4/Desktop/manaos_integrations/README.md を VS Code で開いて
```

期待結果:

- `vscode_open_file` が呼び出される
- VS Code で対象ファイルが開く

### ケース 3: 許可コマンドの実行

入力例:

```text
PowerShellで "Get-Location" を実行して結果を教えて
```

期待結果:

- `execute_command` が呼び出される
- コマンドが成功し、標準出力が返る

### ケース 4: 危険コマンドのブロック

入力例:

```text
PowerShellで Remove-Item -Recurse C:/Users/mana4/Desktop/tmp を実行して
```

期待結果:

- `execute_command` は拒否される
- 応答にブロック理由が含まれる
- `logs/tool_server_security.log` に `command_blocked` が記録される

## 判定基準

- 4 ケース中 4 ケースが期待通りなら合格
- 1 件でも不一致があれば不合格として、下記ログを添付して再調査
  - `logs/tool_server_security.log`
  - Open WebUI ブラウザ開発者ツールの Network/Console

## 手動結果の記録（推奨）

手動チャット入力例は `docs/checklists/OPENWEBUI_MANUAL_PROMPTS.md` を参照する。

一括実行（自動チェック + 手動結果記録 + 最終判定）を使う場合:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_openwebui_acceptance_pipeline.ps1 -Case1 pass -Case2 pass -Case3 pass -Case4 pass -Notes "manual chat completed"
```

VS Code タスク実行でも同等に実行可能:

- `OpenWebUI: Acceptance pipeline (full)`
- `OpenWebUI: Acceptance pipeline (manual only)`
- `OpenWebUI: Check latest acceptance verdict`
- `OpenWebUI: Notify latest acceptance status`
- `ManaOS: OpenWebUI 最新判定確認（strict PASS）`
- `ManaOS: OpenWebUI 手動記録（対話）`
- `ManaOS: OpenWebUI 手動記録（対話 strict PASS）`

ショートカット:

- `Ctrl+Shift+B` でデフォルトの `OpenWebUI: Acceptance pipeline (full)` を実行
- 最終判定だけ見たいときは `OpenWebUI: Check latest acceptance verdict` を実行
- 通知用1行サマリーを出すときは `OpenWebUI: Notify latest acceptance status` を実行
- リリースゲート用途で PASS 必須判定にする場合は `ManaOS: OpenWebUI 最新判定確認（strict PASS）` を実行
- 手動4ケース結果をその場で入力して記録・最終化する場合は `ManaOS: OpenWebUI 手動記録（対話）` を実行
- PASS必須で同時確認する場合は `ManaOS: OpenWebUI 手動記録（対話 strict PASS）` を実行

通知タスク実行時の補足:

- `Reports/OpenWebUI_Acceptance_Latest_Status.txt` を更新
- 出力形式は `acceptance_status=... created_at=... file=...`

自動チェックを省略して手動記録と最終判定だけ行う場合:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_openwebui_acceptance_pipeline.ps1 -SkipAutomated -Case1 pass -Case2 pass -Case3 pass -Case4 pass -Notes "manual-only finalize"
```

手動4ケース実施後、以下で最新レポートへ記録を追記する。

```powershell
powershell -ExecutionPolicy Bypass -File .\record_openwebui_manual_cases.ps1 -Case1 pass -Case2 pass -Case3 pass -Case4 pass -Notes "OpenWebUI chat run completed"
```

補足:

- `pass | fail | skip` を各ケースに指定可能
- `Reports/OpenWebUI_Manual_Case_Record_*.json` に証跡 JSON も保存される

## 不合格時の一次対応

1. Tool Server の再起動
   - `powershell -ExecutionPolicy Bypass -File .\START_TOOL_SERVER_HOST.ps1`
2. OpenAPI 再確認
   - `http://127.0.0.1:9503/openapi.json`
3. Open WebUI 側で External Tools を再接続
4. 再度 `run_openwebui_tool_acceptance.ps1` を実行
