# Release Notes (2026-03-01)

## Summary

- Tag `v2.6.2` を作成し、`origin` に反映。
- Pixel7 HTTP スモークの運用性を改善（HTTP-only 実行と ADB one-shot 復旧）。
- profile 判定まわりの案内・BaseUrl 解決を安定化。
- fail-check タスクに `config/secrets.local.ps1` 読み込みと webhook source 監査情報を追加。

## Included Commits

### 1) `9459f02`
`ops: integrate pixel7 smoke/recovery refinements and webhook secret loading`

- `pixel7_http_smoketest.ps1`: `-SkipFallbackActions` / `AutoRecoverAdb` 追加
- `pixel7_check_api_profile.ps1`: BaseUrl 解決改善、旧Gateway時メッセージ改善
- `PIXEL7_HTTP_CONTROL.md`, `docs/guides/PIXEL7_MINIMAL_SECURE_MODE.md`: HTTP-only スモーク導線追記

### 2) `7496944`
`add secrets.local webhook fallback for fail-check task`

- `tools/run_file_secretary_fail_check.ps1`: `config/secrets.local.ps1` 読み込み、session/user webhook source 記録
- `.gitignore`: `config/secrets.local.ps1` を除外
- `config/secrets.local.example.ps1` 追加

### 3) `aa3fb6e`
`wire fail-streak checker to slack webhook with cooldown`

- fail-streak 通知タスク連携の基盤実装。

## Release Status

- Tag push: completed (`v2.6.2`)
- GitHub Release publish: pending (`gh auth` 失効のため)

## Notes

- `gh release create` は認証復旧後に実行してください。
- 推奨コマンド:

```powershell
gh auth login
gh release create v2.6.2 --title "v2.6.2 - Pixel7 Smoke Recovery + Webhook Fallback" --notes-file RELEASE_NOTES_20260301.md
```
