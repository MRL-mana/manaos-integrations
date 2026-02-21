# Local Noise Runbook

ローカル端末固有の生成物で `git status` が汚れる場合の運用手順です。リポジトリには影響を出さず、開発端末だけでノイズを抑制します。

## 1) 一時ファイルを追跡対象から外す（ローカルのみ）

```powershell
git update-index --skip-worktree <path>
```

例:

```powershell
git update-index --skip-worktree .env
git update-index --skip-worktree logs/local_debug.log
```

## 2) 元に戻す

```powershell
git update-index --no-skip-worktree <path>
```

## 3) 未追跡ファイルは .git/info/exclude を使う

`.git/info/exclude` はローカル専用です。リモートには共有されません。

```text
# local artifacts
logs/
*.local.json
*.tmp
```

## 4) 確認コマンド

```powershell
git status --short
git ls-files -v | Select-String "^[S]"
```

## 5) 注意点

- 共有すべき設定ファイルまで `skip-worktree` にしない。
- チーム共通の除外は `.gitignore` に反映する。
- 端末固有のノイズだけをこの runbook で抑える。
