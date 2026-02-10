# 監査ローテ: moltbot_audit の古い日付フォルダをアーカイブする
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\rotate_audit.ps1
# 保持日数: $env:MOLTBOT_AUDIT_KEEP_DAYS = "30"（デフォルト 30 日）
# 削除する場合: $env:MOLTBOT_AUDIT_DELETE = "1"

$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq "deploy") { Set-Location ..\.. }
python moltbot_gateway\deploy\rotate_audit.py
