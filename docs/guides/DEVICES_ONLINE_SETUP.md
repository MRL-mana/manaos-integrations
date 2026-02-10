# デバイスをオンラインにする手順

オーケストレーターで各デバイスを「オンライン」表示にするための起動手順です。

## 起動コマンド一覧（簡潔）

| デバイス | どこで | コマンド |
|----------|--------|----------|
| **3/6 まとめて** | 母艦 | `.\quick_start_devices.ps1` または `quick_start_devices.bat` |
| **ManaOS (5106)** | 母艦 | `.\start_orchestrator_5106.ps1` |
| **Pixel 7 (5122)** | 母艦 | `.\start_pixel7_bridge.ps1`（USB）/ `.\start_pixel7_bridge_tailscale.ps1`（Tailscale） |
| **X280 (5120)** | X280 PC | `python x280_node_manager.py` または SSOT API を 5120 で起動 |
| **Konoha (5106)** | このはサーバー | `python unified_orchestrator.py`（作業ディレクトリ: manaos_integrations 等） |
| **MoltBot Gateway (8088)** | 母艦 or このは | 秘書ファイル整理に必要。母艦: **`moltbot_gateway\deploy\start_gateway_mothership.bat`** で起動。.env に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` と `MOLTBOT_GATEWAY_SECRET=local_secret`。詳細は `docs/integration/MOLTBOT_MANAOS_INTEGRATION_DESIGN.md`。 |

---

## 一覧

| デバイス | ポート/接続先 | 起動方法 |
|----------|----------------|----------|
| **母艦** | (ローカル) | 常にオンライン扱い |
| **Pixel 7** | localhost:5122（母艦でブリッジ） | 下記 A |
| **X280** | 100.127.121.20:5120 | X280 PC で 5120 を起動 |
| **Konoha** | 100.93.120.33:5106 | このはサーバーで 5106 を起動 |
| **ManaOS** | localhost:5106 | このはで 5106 を起動 |

---

## A. Pixel 7（USB 接続時）

**母艦で実行（Pixel 7 を USB で接続した状態）:**

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
.\start_pixel7_bridge.ps1
```

- **自動起動**: `scripts\install_pixel7_bridge_autostart.ps1` でタスク登録（ログオン時起動）。詳しくは [PIXEL7_INTEGRATION_GUIDE.md](./PIXEL7_INTEGRATION_GUIDE.md) の「運用を楽にする」を参照。

---

## B. X280（5120）

X280 用の API/Node Manager を **X280 の PC**（Tailscale IP 100.127.121.20）で起動します。

- `x280_node_manager.py` または SSOT API をポート 5120 で起動。
- 母艦から `http://100.127.121.20:5120/health` にアクセスできるとオンライン表示になります。

---

## C. Konoha（このは・5106）

このはサーバー（100.93.120.33）で Unified Orchestrator を 5106 で起動します。

```bash
# このはサーバー上
python unified_orchestrator.py   # ポート 5106
```

- 母艦から `http://100.93.120.33:5106/health` にアクセスできるとオンライン表示になります。

---

## D. ManaOS（5106）

**母艦で起動する場合（ManaOS をオンライン表示）:**

```powershell
.\start_orchestrator_5106.ps1
```

- このはサーバー上の ManaOS / 5106 を起動してもよい（その場合は 100.93.120.33:5106 で Konoha として表示）。

---

## 確認コマンド

全デバイスの疎通をまとめて確認:

```powershell
.\scripts\check_devices_online.ps1
```

オーケストレーターの状態（MCP）: `device_discover` を実行するとオンライン数が表示されます。

## 定期確認（任意）

30分ごとにデバイス状態を確認し、ログに残すタスクを登録（管理者で実行）:

```powershell
.\scripts\install_devices_health_check_schedule.ps1
```

ログは `logs\devices_health_YYYYMMDD.log` に追記されます。
