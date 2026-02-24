# Pixel7 MacroDroid（HTTP制御用）最小テンプレ（迷わない版）

目的: 母艦→HTTP（Termux API Gateway）→MacroDroid の Intent で、ADB無しのリモコン操作を成立させる。

## 1本だけ作ればOK（Intent受信→cmd分岐）

### トリガー

- **Intent Received**
  - Action: `com.manaos.PIXEL7_MACRO`
  - Extras: `cmd`（String）

### 分岐（cmd）

以下の `cmd` を条件にして、対応する操作を割り当てる。

- `Wake`
- `Home`
- `Back`
- `Recents`
- `ExpandNotifications`
- `ExpandQuickSettings`
- `CollapseStatusBar`

※これらは `GET /api/macro/commands` でも確認できる。

### アクション（おすすめ割当）

- `Wake`: 画面オン（または電源ボタン相当）
- `Home`: Home
- `Back`: Back
- `Recents`: Recent Apps
- `ExpandNotifications`: Notifications
- `ExpandQuickSettings`: Quick Settings
- `CollapseStatusBar`: 戻る（複数回）またはステータスバー閉じる操作

## 権限

- 画面操作系は **アクセシビリティ権限** が必要（MacroDroidの案内に従う）

## 動作確認（母艦）

- まずHTTPだけで送る:
  - VS Codeタスク: 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP）」
- cmd一覧を見る:
  - VS Codeタスク: 「ManaOS: Pixel7 MacroDroid cmd一覧（HTTP）」
- まとめて疎通確認（Intent送信）:
  - VS Codeタスク: 「ManaOS: Pixel7 MacroDroid 疎通プローブ（HTTP）」
- MacroDroid未設定/HTTP不調時でも動くブリッジ:
  - VS Codeタスク: 「ManaOS: Pixel7 MacroDroid cmd送信（HTTP→ADB）」

extras を使う場合は `ExtrasJson` に JSON を入れる（例: `{\"x\":123}`）。
