# Pixel7 画面を母艦に出す（scrcpy）

## 最短（VS Codeタスク）

- **自動**: 「ManaOS: Pixel7 画面ミラー（自動scrcpy）」
- **自動・縦長固定**: 「ManaOS: Pixel7 画面ミラー（自動scrcpy/縦長）」
- **停止**: 「ManaOS: Pixel7 画面ミラー停止（scrcpy kill）」

## 外出先でも操作（Tailscale only）

- **ワンボタン（外出）**: 「ManaOS: Pixel7 外出モード（ワンボタン: keepalive + scrcpy watch）」
- **外出フル常駐**: 「ManaOS: Pixel7 外出フル常駐（keepalive + scrcpy watch + reboot watch）」
- **外出・ADB復旧**: 「ManaOS: Pixel7 外出モード 無線ADB復旧（Tailscaleのみ）」
- **外出・keepalive**: 「ManaOS: Pixel7 外出モード ADB keepalive開始（Tailscaleのみ/バックグラウンド）」
- **外出・ミラー監視**: 「ManaOS: Pixel7 外出モード 画面ミラー監視（scrcpy watch / 自動復帰）」
- **外出・ミラー監視（バックグラウンド）**: 「ManaOS: Pixel7 外出モード 画面ミラー監視開始（バックグラウンド）」
- **外出・ミラー監視停止**: 「ManaOS: Pixel7 外出モード 画面ミラー監視 停止（scrcpy watch stop）」

## 停止（まとめて止める）

- 「ManaOS: Pixel7 一括停止（watch/keepalive/scrcpy/rebootwatch）」

※外出モードのバックグラウンド監視は、端末の発熱を抑えるため **端末画面OFF**（scrcpy `--turn-screen-off`）を有効化しています。

## 監視ログ/状態

- scrcpyログ: `manaos_integrations/logs/scrcpy_auto_*.out.log` / `scrcpy_auto_*.err.log`
- 監視ログ: `manaos_integrations/logs/pixel7_scrcpy_watch_YYYYMMDD.log`
- 監視ステータス: `manaos_integrations/.pixel7_scrcpy_watch.status.json`

## ダッシュボード

- 「ManaOS: Pixel7 ダッシュボード（状態/ログまとめ）」
  - ADB接続状況 / watchのstatus.json / 最新scrcpyログ / 再起動バンドル一覧 を1画面で確認

## 完全HTTP制御（HTTP優先→失敗時だけADB）

- まずは Pixel側でHTTP受け口（Termux）を常駐させて、母艦→HTTPで操作します
- タスク:
  - 「ManaOS: Pixel7 HTTP Health（API Gateway）」
  - 「ManaOS: Pixel7 HTTP Status（API Gateway）」
  - 「ManaOS: Pixel7 OpenWebUIを開く（HTTP→ADB 自動フォールバック）」
  - 「ManaOS: Pixel7 HTTP Shortcutsを開く（HTTP→ADB 自動フォールバック）」

セットアップ手順は `manaos_integrations/PIXEL7_HTTP_CONTROL.md` を参照。

## 再起動ログ回収（原因調査）

- **監視開始**: 「ManaOS: Pixel7 再起動ログ監視開始（バックグラウンド）」
- **外出モード監視開始**: 「ManaOS: Pixel7 外出モード 再起動ログ監視開始（Tailscaleのみ/バックグラウンド）」
- **停止**: 「ManaOS: Pixel7 再起動ログ監視 停止」
- 保存先: `manaos_integrations/logs/pixel7_reboots/<timestamp>_<serial>/`

## 端末が勝手に落ちる/再起動する時の復旧導線（ADBで設定画面を開く）

- 「ManaOS: Pixel7 Tailscaleアプリ情報を開く（ADB）」
  - ここから **バッテリー最適化: 制限なし** に手動で変更するのが一番効きます
- 「ManaOS: Pixel7 バッテリー最適化設定を開く（ADB）」
- 「ManaOS: Pixel7 開発者向けオプションを開く（ADB）」

## 省電力で切断しやすい時のワンボタン（ADBで即適用）

- 「ManaOS: Pixel7 充電中スリープ無効（Stay awake ON / ADB）」
- 「ManaOS: Pixel7 Doze無効化（deviceidle disable / ADB）」
- 「ManaOS: Pixel7 VPN設定を開く（ADB）」

## 録画（開始→停止→保存）

- **開始（手動停止）**: 「ManaOS: Pixel7 画面録画開始（手動停止）」
- **停止→保存**: 「ManaOS: Pixel7 画面録画停止→保存（手動停止）」
- **固定秒数**: 「ManaOS: Pixel7 画面録画（10秒）」「ManaOS: Pixel7 画面録画（30秒）」

## “見せて質問”（カメラ/画面 → Vision）

- **カメラを開く**: 「ManaOS: Pixel7 カメラを開く（ADB）」
- **画面に質問**: 「ManaOS: Pixel7 画面に質問（Vision/Ollama）」
  - カメラプレビューを開いた状態で実行すれば「カメラで見せて質問」になる
- **カメラで質問（ワンボタン）**: 「ManaOS: Pixel7 カメラで質問（Vision/Ollama）」

## リモコン操作（ADBキー送信）

- 「ManaOS: Pixel7 リモコン（Home）」
- 「ManaOS: Pixel7 リモコン（Back）」
- 「ManaOS: Pixel7 リモコン（Recents）」
- 「ManaOS: Pixel7 リモコン（通知を開く）」
- 「ManaOS: Pixel7 リモコン（クイック設定を開く）」
- 「ManaOS: Pixel7 リモコン（通知/設定を閉じる）」
- 「ManaOS: Pixel7 リモコン（画面点灯/Wake）」
- 「ManaOS: Pixel7 リモコン（スワイプ解除/安全版）」
- 「ManaOS: Pixel7 リモコン（音量+）」 / 「ManaOS: Pixel7 リモコン（音量-）」 / 「ManaOS: Pixel7 リモコン（ミュート）」
- 「ManaOS: Pixel7 アプリ起動（HTTP Shortcuts）」
- 「ManaOS: Pixel7 アプリ起動（OpenWebUI）」

## 仕組み

- scrcpy は `Desktop\scrcpy\scrcpy-win64-v3.3.4\scrcpy.exe` を使用
- ADB接続先は以下を順に試行（見つかったらそれで起動）
  1. `PIXEL7_ADB_SERIAL`（環境変数がある場合）
  2. Tailscale: `PIXEL7_TAILSCALE_IP:5555`（デフォルト `100.84.2.125:5555`）
  3. 同一Wi‑Fi（USB接続がある場合、端末の `wlan0` IPv4 を自動検出して `IP:5555`）
  4. USB接続（シリアル直指定）

## 縦長固定について

- scrcpy v3.3.4 では `--lock-video-orientation` は削除されています
- 縦長固定は `--capture-orientation=@0` を使用（端末の自然方向を基準にロック）

## 手動起動（PowerShell）

- 自動: `powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\pixel7_scrcpy_auto.ps1`
- 自動・縦長: `powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\pixel7_scrcpy_auto.ps1 -Portrait -KillExisting`
- 直指定: `powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\pixel7_scrcpy_wireless.ps1 -DeviceSerial 192.168.3.141:5555 -Portrait`
