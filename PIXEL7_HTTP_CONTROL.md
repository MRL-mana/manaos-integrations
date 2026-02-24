# Pixel7 完全HTTP制御（MVP）

目的: 母艦→HTTP→（必要時だけADB）に寄せて、Pixel7を「遠隔制御ノード」として安定運用する。

## 構成（ハイブリッド）

- Pixel側: `pixel7_api_gateway.py` をTermuxで常駐（HTTP受信）
- Pixel側: 画面操作など“アプリ権限が必要な操作”は MacroDroid のマクロに委譲（Intent受信）
- 母艦側: `pixel7_http_control.ps1` でHTTP経由コマンド（Status / OpenURL / Macro）を実行

## Pixel側セットアップ（Termux）

- Termux をインストール
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

- Termux:Boot を使って `~/.termux/boot/` に起動スクリプトを置く
- 端末スリープで止まる場合は `termux-wake-lock` を検討

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
- 停止（pkillでbest-effort）: `pwsh -File .\manaos_integrations\pixel7_termux_stop_http_gateway.ps1`

### VS Codeタスク（おすすめ）

- 「ManaOS: Pixel7 HTTP トークン生成（表示）」
- 「ManaOS: Pixel7 HTTP Gateway 配置（adb push）」

- 「ManaOS: Pixel7 TermuxでHTTP Gateway起動（ADB補助）」
- 「ManaOS: Pixel7 TermuxでHTTP Gateway停止（ADB補助）」

- 「ManaOS: Pixel7 HTTP 起動（セットアップ→起動→監視）」

※母艦側でトークンファイルがある場合、配置タスクは `api_token.txt` としてPixel側にも同梱します。

- 「ManaOS: Pixel7 Termuxを開く（ADB / HTTP復旧用）」
- 「ManaOS: Pixel7 HTTP スモークテスト（health/status/fallback）」
- 「ManaOS: Pixel7 HTTP 監視開始（バックグラウンド）」
- 「ManaOS: Pixel7 外出モード HTTP 監視開始（Tailscaleのみ/バックグラウンド）」
- 「ManaOS: Pixel7 HTTP 監視停止」
- 「ManaOS: Pixel7 外出フル常駐+HTTP（keepalive + scrcpy + reboot + http watch）」
- 「ManaOS: Pixel7 URLを開く（HTTP→ADB 自動フォールバック）」
- 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP）」
- 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP→ADB）」

## セキュリティ

- Bearerトークン必須（`PIXEL7_API_TOKEN`）
- 既定で Tailscale IP帯以外からのアクセスは拒否（`PIXEL7_API_TAILSCALE_ONLY=1`）
- 危険な `/api/execute` は既定無効（必要なら `PIXEL7_API_ALLOW_EXEC=1`）
