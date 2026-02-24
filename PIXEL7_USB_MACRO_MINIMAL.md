# Pixel 7（MacroDroid）USB接続トリガー：最小運用（迷わない版）

## 目的
USBを挿したら「接続→確認→操作」のコックピットを自動で開く。

## 前提
- Pixel 7にTailscaleがログイン済み
- Chromeが使える

## マクロ（1本だけ作る）
### トリガー
- **USB接続** → **デバイス接続時**

### アクション（この順で固定）
1. **アプリ起動**: Tailscale
2. **待機**: 3秒
3. **Webページを開く**（Chrome）
   - `http://100.73.247.100:9502/emergency`
4. （任意）**アプリ起動**: HTTP Shortcuts
   - ホームに置いた4ボタン（Status / Clear VRAM / Emergency Stop / OpenWebUI）だけ押す運用に寄せる

## ホームに置くもの（これだけ）
- 📊 Remi Status
- 🧹 Clear VRAM
- 🚨 Emergency Stop
- OpenWebUI (HTTPS)

## PC側ワンボタン（OpenWebUI URL更新→Pixelへ反映）
- 初回（Importまで開く）
   - `powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\pixel7_minimal_quick.ps1`

- 日常（URL同期だけ。Importは開かない）
   - `powershell -NoProfile -ExecutionPolicy Bypass -File .\manaos_integrations\pixel7_minimal_quick.ps1 -SkipOpenWebUIStart -SkipImport`

> Pixelがロック中だとImport画面が出ないので、実行中は端末を解除して必要ならImport/OKをタップ。
