# Release Notes (2026-03-01 / v2.6.3)

## Summary

- fail-check 通知で既存の `MANAOS_WEBHOOK_*` 設定を再利用できるよう改善。
- `README.md` の表示バージョンを `v2.6.2` に同期。
- `v2.6.2` リリース後の追補を `v2.6.3` として整理。

## Included Commits (since v2.6.2)

### 1) `32c6e91`
`reuse existing MANAOS_WEBHOOK settings for fail-check alerts`

- `tools/notify_slack_webhook.ps1`
- `tools/run_file_secretary_fail_check.ps1`

`SLACK_WEBHOOK_URL` が無い場合でも `MANAOS_WEBHOOK_URL` 系設定を活用できるようにし、通知運用の一貫性を改善。

### 2) `e1cdfc2`
`docs: bump README version to v2.6.2`

- `README.md` の先頭バージョン表記を現行リリースに合わせて更新。

### 3) `b0c1113`
`docs: add release notes for v2.6.2`

- `RELEASE_NOTES_20260301.md` を追加し、`v2.6.2` の変更点を記録。

## Release Status

- Target tag: `v2.6.3`
- Base branch: `master`
