# ManaOS 自動常駐（Windows起動後に自動で全部緑へ）

この手順は、Windows起動（またはログオン）後に ManaOS の主要サービス群を自動起動するためのものです。

対象: `manaos_integrations/start_vscode_cursor_services.py`
- Unified API / LLM Routing / MRL Memory / Learning System / Video Pipeline をまとめて起動

## 1) インストール（タスク登録）

推奨は「管理者 PowerShell + 最上位の特権（UACで止まりにくい）」です。

- ログオン時に起動（おすすめ）

`powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\install_vscode_cursor_services_autostart.ps1 -Trigger Logon`

- PC起動時に起動（早めに立ち上げたい場合）

`powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\install_vscode_cursor_services_autostart.ps1 -Trigger Startup`

### 管理者で実行できない場合

権限は下がりますが、非管理者でも登録できます。

`powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\install_vscode_cursor_services_autostart.ps1 -Trigger Logon -RunLevel Limited`

（補足）`-RunLevel` は `Highest` / `Limited` のどちらかです。

## 2) 手動起動（今すぐ）

`Start-ScheduledTask -TaskName ManaOS_VSCodeCursor_Services`

## 3) 確認

`Get-ScheduledTask -TaskName ManaOS_VSCodeCursor_Services`

必要なら直後にヘルス確認:

`C:/Users/mana4/Desktop/.venv/Scripts/python.exe manaos_integrations/check_services_health.py`

## 4) アンインストール（タスク削除）

`powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\uninstall_vscode_cursor_services_autostart.ps1`

## メモ

- `.venv` がある場合は `Desktop/.venv/Scripts/python.exe` を優先して実行するので、依存ズレが起きにくいです。
- Unified API の 9502 が占有されている場合は、起動マネージャー側で解放を試みます。自動常駐タスク自体も「最上位の特権」で動くため、UAC で止まりにくくなります。
