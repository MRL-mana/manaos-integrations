# Pixel7 完全HTTP制御（MVP）

目的: 母艦→HTTP→（必要時だけADB）に寄せて、Pixel7を「遠隔制御ノード」として安定運用する。

## 構成（ハイブリッド）

- Pixel側: `pixel7_api_gateway.py` をTermuxで常駐（HTTP受信）
- Pixel側: 画面操作など“アプリ権限が必要な操作”は MacroDroid のマクロに委譲（Intent受信）
- 母艦側: `pixel7_http_control.ps1` でHTTP経由コマンド（Status / OpenURL / Macro）を実行

## Pixel側セットアップ（Termux）

- Termux をインストール（推奨: **F-Droid版**。Play版だと Termux:Boot などのアドオンが揃わないことがあります）
- Termux:API をインストール（可能なら）
- 依存導入

  - `pkg update`
  - `pkg install python`
  - `pip install fastapi uvicorn`

- トークン設定（例）

  - `export PIXEL7_API_TOKEN='(長いランダム文字列)'`

- 起動（Tailscale接続前提 / デフォルト: port 5122）

  - `export PIXEL7_API_PORT=5122`
  - `python pixel7_api_gateway.py`

### 起動スクリプト（推奨）

- `manaos_integrations/termux/start_pixel7_api_gateway.sh`
  - これをPixelの `$HOME/start_pixel7_api_gateway.sh` として配置して実行
- `manaos_integrations/termux/boot_start_pixel7_api_gateway.sh`
  - Termux:Boot 用。`~/.termux/boot/` に置くと再起動後に自動起動できます

### 自動起動（任意）

- Termux:Boot を使って `~/.termux/boot/` に起動スクリプトを置く（F-Droidで `Termux:Boot` をインストール）
- 端末スリープで止まる場合は `termux-wake-lock` を検討

補足:

- 再起動後、初回は依存導入（pip install）で `/health` が返るまで数分かかることがあります
- Termux:Boot が動いているかは `/storage/emulated/0/Download/pixel7_termux_boot.log` を見ると確認できます
- 再起動テストは `pwsh -File .\manaos_integrations\pixel7_http_autostart_reboot_test.ps1` が便利です

## MacroDroid 連携（Intent受信）

- MacroDroidで新規マクロ（最小）
  - トリガ: **Intent Received**
    - Action: `com.manaos.PIXEL7_MACRO`
    - Extra: `cmd`（文字列）
  - 条件（分岐）: `cmd == 'Home'` / `Back` / `Recents` / `Wake` / `ExpandNotifications` / `ExpandQuickSettings` / `CollapseStatusBar`
  - アクション: 各操作に対応する「Homeボタン」「戻る」「最近」「通知」「クイック設定」など

※画面操作系はアクセシビリティ権限が必要です。

- HTTP側からは `POST /api/macro/broadcast` を使う

最小テンプレ手順: `manaos_integrations/PIXEL7_MACRODROID_HTTP_MINIMAL.md`

## 母艦側（PowerShell）

### 環境変数（推奨）

- `PIXEL7_TAILSCALE_IP` : Pixel7のTailscale IPv4（例: `100.84.2.125`）
- `PIXEL7_API_PORT` : 既定 `5122`
- `PIXEL7_API_TOKEN` : Pixel側と同じトークン

※母艦側は `manaos_integrations/.pixel7_api_token.txt` があれば自動で読みます（タスクのトークン生成で作られます）。

### 実行例

- Health: `pwsh -File .\manaos_integrations\pixel7_http_control.ps1 -Action Health`
- Status: `pwsh -File .\manaos_integrations\pixel7_http_control.ps1 -Action Status`
- URLを開く: `pwsh -File .\manaos_integrations\pixel7_http_control.ps1 -Action OpenUrl -Url 'https://example.com'`
- OpenWebUIを開く: `pwsh -File .\manaos_integrations\pixel7_http_control.ps1 -Action OpenOpenWebUI`
- MacroDroidへ命令: `pwsh -File .\manaos_integrations\pixel7_http_control.ps1 -Action BroadcastMacro -MacroCmd 'MyCommand'`

### Termux操作（ADB補助 / 任意）

Pixel側でTermuxを開いてコマンドを打つのが面倒なときの補助です（HTTPゲートウェイの起動/停止）。

- 起動（DestDirへ移動→chmod→起動）: `pwsh -File .\manaos_integrations\pixel7_termux_start_http_gateway.ps1`
- ログ付きでバックグラウンド起動（推奨パス）: `pwsh -File .\manaos_integrations\pixel7_termux_start_http_gateway.ps1 -LogPath /storage/emulated/0/Download/pixel7_api_gateway_termux.log`
- 停止（pkillでbest-effort）: `pwsh -File .\manaos_integrations\pixel7_termux_stop_http_gateway.ps1`

### VS Codeタスク（おすすめ）

- 「ManaOS: Pixel7 HTTP トークン生成（表示）」
- 「ManaOS: Pixel7 HTTP Gateway 配置（Termux bootstrap）」
  - 推奨: Termuxの `$HOME` に配置されます（/sdcard権限やnoexec問題を回避）

- （任意/旧）「ManaOS: Pixel7 HTTP Gateway 配置（adb push）」
  - `/sdcard/Download/...` へ配置します。端末設定次第でTermuxから読めない/実行できない場合があります。

- 「ManaOS: Pixel7 TermuxでHTTP Gateway起動（ADB補助）」
- 「ManaOS: Pixel7 TermuxでHTTP Gateway停止（ADB補助）」

- 「ManaOS: Pixel7 HTTP 起動（セットアップ→起動→監視）」

※母艦側でトークンファイルがある場合、配置タスクは `api_token.txt` としてPixel側にも同梱します。

- 「ManaOS: Pixel7 Termuxを開く（ADB / HTTP復旧用）」
- 「ManaOS: Pixel7 Termux ストレージ権限セットアップ（termux-setup-storage）」
- 「ManaOS: Pixel7 Termux バックグラウンド許可（ADB）」
- 「ManaOS: Pixel7 Termux+HTTP Shortcuts バックグラウンド許可（ADB）」
- 「ManaOS: Pixel7 HTTP スモークテスト（health/status/fallback）」
- 「ManaOS: Pixel7 HTTP 監視開始（バックグラウンド）」
- 「ManaOS: Pixel7 外出モード HTTP 監視開始（Tailscaleのみ/バックグラウンド）」
- 「ManaOS: Pixel7 HTTP 監視停止」
- 「ManaOS: Pixel7 半自律チェック（確認→復旧→通知）」
  - `pixel7_edge_onebutton.ps1` を実行し、`health確認 →（必要時）無線ADB復旧 + Termux起動補助 → 再health確認 → smoketest` を1本で実行
  - 実行結果は `logs/pixel7_edge_onebutton_latest.json` と `logs/pixel7_edge_onebutton_history.jsonl` に保存
  - `-AutoRecoverOnFailure` で自己復旧を有効化（タスク既定）
  - 通知は `MANAOS_WEBHOOK_URL` / `MANAOS_WEBHOOK_FORMAT` / `MANAOS_WEBHOOK_MENTION` を使って失敗時に送信（`-NotifyOnSuccess` で成功通知も可）
- 「ManaOS: Pixel7 半自律監視開始（5分/バックグラウンド）」
  - `pixel7_edge_watch.ps1` を常駐実行し、5分ごとに `pixel7_edge_onebutton.ps1` を自動実行
  - 連続失敗2回で監視間隔を短縮（300秒→60秒）、復帰後は300秒へ自動復元
  - 段階復旧を実行（既定）
    - 失敗2回以上: detailに応じた強制Gateway復旧（`status_file_missing` / `status_parse_failed`）
    - 失敗5回以上: 強復旧（無線ADB復旧 + Termux起動補助）
    - 失敗8回以上: （`-EnableRebootTestRecovery` 指定時のみ）再起動テスト復旧
  - 失敗通知は状態遷移時に即時送信し、連続失敗中は15分クールダウンで追撃通知
  - `status_file_missing` / `status_parse_failed` が続く場合は、クールダウン付きで `無線ADB復旧 + Termux起動補助` を強制実行
  - 監視状態は `.pixel7_edge_watch.status.json`、ログは `logs/pixel7_edge_watch_YYYYMMDD.log`
  - 通知は「状態遷移時のみ」（正常→異常、異常→正常）に送るため、通知スパムを抑制
- 「ManaOS: Pixel7 半自律監視開始（攻め: 再起動復旧ON）」
  - `-EnableRebootTestRecovery` を付けた監視開始タスク
  - 長時間異常が継続した場合、再起動テストを使う最終段の自動復旧まで実施
- 「ManaOS: Pixel7 外出モード 半自律監視開始（攻め: 再起動復旧ON/Tailscale）」
  - 攻めモード + `-RemoteOnly`（Tailscale経路前提）
- 「ManaOS: Pixel7 半自律監視（通常）ワンボタン」
  - 監視開始（通常）→状態確認を順に実行
- 「ManaOS: Pixel7 半自律監視（攻め）ワンボタン」
  - 監視開始（攻め）→状態確認を順に実行
- 「ManaOS: Pixel7 半自律監視開始（自動切替: 昼通常/夜攻め）」
  - `pixel7_edge_watch_profile_start.ps1 -Profile Auto` を実行
  - 昼（7:00-21:59）は通常、夜（22:00-6:59）は攻め（再起動復旧ON）で開始
- 「ManaOS: Pixel7 外出モード 半自律監視開始（自動切替: 昼通常/夜攻め）」
  - 上記に `-RemoteOnly` を付与した外出モード
- 「ManaOS: Pixel7 半自律監視（自動切替）ワンボタン」
  - 自動切替監視開始→状態確認を順に実行
- 「ManaOS: Pixel7 半自律監視開始（自動切替+週次しきい値）」
  - `-EnableWeeklyThresholdProfile` を有効化
  - 平日: しきい値 `2/5/8`（degraded/strong/reboot）
  - 休日: しきい値 `3/6/10`（degraded/strong/reboot）
  - `-RebootRecoveryMode NightWeekendOnly` 指定時は「夜かつ休日」の場合のみ再起動復旧を有効化
  - `-EnableHolidayAsWeekend -HolidayDateFile config/pixel7_holidays_jp.txt` で、祝日を休日扱いにできる
  - 祝日ファイルは `config/pixel7_holidays_jp.txt`（`yyyy-MM-dd` を1行1件）
  - 祝日ファイル更新は `update_pixel7_holidays_jp.ps1` で実行
    - 例: `pwsh -File .\update_pixel7_holidays_jp.ps1 -IncludeNextYear`
    - タスク: 「ManaOS: Pixel7 祝日ファイル更新（今年+来年）」
  - 年次自動更新（年末実行）
    - 登録: `install_pixel7_holidays_update_task.ps1`
    - 状態: `status_pixel7_holidays_update_task.ps1`
    - 解除: `uninstall_pixel7_holidays_update_task.ps1`
    - タスク: 「ManaOS: Pixel7 祝日更新タスク登録（年次）」 / 「ManaOS: Pixel7 祝日更新タスク状態確認」 / 「ManaOS: Pixel7 祝日更新タスク解除」
    - ワンボタン: 「ManaOS: Pixel7 祝日更新タスク登録→状態確認（ワンボタン）」 / 「ManaOS: Pixel7 祝日更新タスク解除→未登録確認（ワンボタン）」
  - 再登録保険（ガード: 月次）
    - 登録: `install_pixel7_holidays_update_guard_task.ps1`
    - 状態: `status_pixel7_holidays_update_guard_task.ps1`
    - 解除: `uninstall_pixel7_holidays_update_guard_task.ps1`
    - タスク: 「ManaOS: Pixel7 祝日ガード タスク登録」 / 「ManaOS: Pixel7 祝日ガード タスク状態確認」 / 「ManaOS: Pixel7 祝日ガード タスク解除」
    - ワンボタン: 「ManaOS: Pixel7 祝日更新ガード登録→状態確認（ワンボタン）」 / 「ManaOS: Pixel7 祝日更新ガード解除→未登録確認（ワンボタン）」
    - 権限不足で `HIGHEST` 登録に失敗した場合は、自動で `LIMITED` へフォールバックして登録
    - 無人運用が必要な場合は `-RunAsSystem` を付与（ログオン有無に依存しない実行）
      - 権限不足で `SYSTEM` 登録に失敗した場合は、既定で現在ユーザーに自動フォールバック
      - `SYSTEM` 固定で失敗時に止めたい場合は `-NoFallbackToCurrentUser` を付与
    - 既定はバッテリでも実行継続（旧挙動に戻す場合は `-KeepBatteryRestrictions`）
  - 統合ワンボタン（運用開始/終了）
    - 開始: 「ManaOS: Pixel7 祝日運用セットアップ（年次+ガード）」
    - 終了: 「ManaOS: Pixel7 祝日運用クリーンアップ（年次+ガード）」
  - R12健全性監視（5分間隔）
    - 登録: `install_r12_health_watch_task.ps1`
    - 状態: `status_r12_health_watch_task.ps1`
    - 解除: `uninstall_r12_health_watch_task.ps1`
    - タスク: 「ManaOS: R12 Health Watch タスク登録（5分）」 / 「ManaOS: R12 Health Watch タスク状態確認」 / 「ManaOS: R12 Health Watch 単発実行」 / 「ManaOS: R12 Health Watch タスク解除」
      - ワンボタン: 「ManaOS: R12 Health Watch 登録→状態確認（ワンボタン）」 / 「ManaOS: R12 Health Watch 解除→未登録確認（ワンボタン）」
      - 統合ワンボタン: 「ManaOS: R12 Health Watch 運用セットアップ（ワンボタン）」 / 「ManaOS: R12 Health Watch 運用クリーンアップ（ワンボタン）」
      - 運用チェック: 「ManaOS: R12 Health Watch 運用チェック（状態+ログ末尾）」
      - JSONチェック: 「ManaOS: R12 Health Watch 運用チェック（JSON）」
        - 出力: `logs/r12_health_watch_check.latest.json`
        - 正常時は1行要約のみ、異常時のみ赤字要約 + タスク生ログ + ログ末尾20件を表示
    - 実体: `manaos-rpg/scripts/run_r12_health_watch.ps1`（タスクからは `run_r12_health_watch_once.ps1` を呼び出し）
    - ログ: `logs/r12_health_watch_task.jsonl`
      - ローテーション: `-MaxJsonLogSizeMB`（既定20MB）/ `-MaxJsonLogFiles`（既定5世代）
    - 例: `pwsh -File .\install_r12_health_watch_task.ps1 -RunNow`
      - 無人運用: `pwsh -File .\install_r12_health_watch_task.ps1 -RunAsSystem -RunNow`
        - 権限不足で `SYSTEM` 登録に失敗した場合は、既定で現在ユーザーに自動フォールバック
        - `SYSTEM` 固定で失敗時に止めたい場合は `-NoFallbackToCurrentUser` を付与
    - 監視補助タスク: 「ManaOS: Scheduled Tasks 健全性チェック」 / 「ManaOS: Scheduled Tasks 健全性チェック（JSON）」
    - 通知（任意）: `MANAOS_WEBHOOK_URL` / `MANAOS_WEBHOOK_FORMAT` (`generic|slack|discord`) / `MANAOS_WEBHOOK_MENTION` / `MANAOS_NOTIFY_ON_SUCCESS`
      - 既定は「失敗時のみ通知」。成功通知も欲しい場合は `MANAOS_NOTIFY_ON_SUCCESS=1`
  - R12+RL 統合監視（15分間隔 / 異常時通知）
    - クイックチェック実体: `check_r12_rl_ops_watch_quick.ps1`
      - `status_r12_rl_ops.ps1 -Json` を実行し、1行サマリー + JSON (`logs/r12_rl_ops_status.latest.json`) を更新
      - 失敗時は `MANAOS_WEBHOOK_URL` 系設定を使って通知（`-NotifyOnSuccess` で成功通知も可）
      - 履歴: `logs/r12_rl_ops_watch.jsonl`
    - 監視タスク登録/状態/解除: `install_r12_rl_ops_watch_task.ps1` / `status_r12_rl_ops_watch_task.ps1` / `uninstall_r12_rl_ops_watch_task.ps1`
    - VS Code タスク: 「ManaOS: R12+RL 監視タスク登録（15分）」 / 「ManaOS: R12+RL 監視タスク状態確認」 / 「ManaOS: R12+RL 監視クイックチェック（通知付き）」 / 「ManaOS: R12+RL 監視タスク解除」
      - ワンボタン: 「ManaOS: R12+RL 監視登録→状態確認（ワンボタン）」 / 「ManaOS: R12+RL 監視解除→未登録確認（ワンボタン）」
- 「ManaOS: Pixel7 外出モード 半自律監視開始（自動切替+週次しきい値）」
  - 上記に `-RemoteOnly` を付与した外出モード
- 「ManaOS: Pixel7 半自律監視（自動切替+週次）ワンボタン」
  - 自動切替+週次しきい値監視開始→状態確認を順に実行
- 「ManaOS: Pixel7 半自律監視 状態確認」 / 「ManaOS: Pixel7 半自律監視 停止」
  - 状態確認: `pixel7_edge_watch_status.ps1`
  - 停止: `pixel7_edge_watch_stop.ps1 -Force`
- 「ManaOS: Pixel7 外出フル常駐+HTTP（keepalive + scrcpy + reboot + http watch）」
- 「ManaOS: Pixel7 URLを開く（HTTP→ADB 自動フォールバック）」
- 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP）」
- 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP→ADB）」

## セキュリティ

- Bearerトークン必須（`PIXEL7_API_TOKEN`）
- 既定で Tailscale IP帯以外からのアクセスは拒否（`PIXEL7_API_TAILSCALE_ONLY=1`）
- 危険な `/api/execute` は既定無効（必要なら `PIXEL7_API_ALLOW_EXEC=1`）
