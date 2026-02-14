# Remi（Pixel 7a）を“アプリ”として使う最短手順

## 目的
- Remiの画面を「アプリっぽく」常時表示・すぐ復帰できる状態にする

---

## A) Floating Apps（チャット壁紙）
1. まず一度だけ開く（Cookieが入り、以後短いURLで動く）
   - `http://100.73.247.100:5050/remi-wallpaper/remi-pixel7-2026`
2. Floating Apps メニューで
   - 「デスクトップとして指定」
   - 「ショートカットを作成」
   - （あれば）「タブを非表示にする」「マイ アプリに追加」
3. 以後はホームのショートカット＝アプリ起動

### 端末再起動時の復帰
- ホームのショートカットから起動
- うまく戻らない場合は Floating Apps の「セッションを復元」

---

## B) HTTP Shortcuts（ボタン操作をアプリ化）
- 端末へ `Download/remi_android_shortcuts.json` を配置済み
- HTTP Shortcuts で Import → ホームにウィジェット配置（※すでに配置済みならスキップ）

### PCからImport画面を開く（おすすめ）
- `powershell -ExecutionPolicy Bypass -File .\pixel7_http_shortcuts_import.ps1`

※ すでにインポート済みの場合、確認ダイアログが出ずに何も起きないように見えることがあります。
※ ホームに「Remi Status」などのHTTP Shortcutsウィジェットが見えていれば、インポート済みの可能性が高いです。

---

## C) PCからの復帰コマンド（ADB）
- Overlay許可＋電池最適化除外
  - `powershell -ExecutionPolicy Bypass -File .\pixel7_set_overlay_and_battery_exempt.ps1`
- Remi画面を開く
  - `powershell -ExecutionPolicy Bypass -File .\pixel7_open_remi_overlay.ps1`

---

## D) ワンコマンド復帰（おすすめ）
- PC側Remi APIの起動（必要なら再起動）→ 端末側の許可確認 → Remi画面復帰までまとめて実行
   - `powershell -ExecutionPolicy Bypass -File .\pixel7_remi_restore.ps1`

※ 端末がロック画面の場合は、スクリプト実行中に端末をロック解除（指紋/PIN）してください。
※ 充電しながら運用するなら、画面がスリープしない設定（Developer optionsの“充電中はスリープしない”相当）もスクリプトが試行します。
