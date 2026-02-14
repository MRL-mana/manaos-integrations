# PICO × NanoKVM 活用 Runbook（起動/復旧の自動化）

目的: OSが落ちている/固まっている状況でも「画面が見える（NanoKVM）」「入力できる（Pico HID）」「電源を切れる/入れられる（電源制御）」の3点セットで復旧できる状態を作る。

## 1) 最小構成（まずここまで）

- NanoKVM: LANからアクセスできる（固定IP推奨）
- Pico HID: ターゲットPCにUSBで直結（HID＋CDCシリアル）
- 母艦(このPC): `manaos-pico-hid` MCP が起動できる

チェック:
- `python -m pico_hid.pc.pico_hid_client pos` が動く（PCバックエンドなら座標が出る）
- `python -m pico_hid.pc.pico_hid_client combo gui r` が動く（Pico側も COMBO 対応）

## 2) 推奨ワークフロー（詰んだら戻す）

- 見る: NanoKVMで現在画面を確認
- 直す: Picoで入力して復旧（Win+R → コマンド実行）
- 切る: どうにもならなければ電源OFF/ON（スマートプラグ or ATX制御）

## 3) すぐ使えるマクロ

マクロ一覧は `python -m pico_hid.pc.pico_hid_macros --help`。

- 起動: `start_services`
- 状態確認: `health_check`
- 統合API再起動: `restart_unified_api`
- 緊急停止: `emergency_stop`
- NanoKVMを開く: `open_nanokvm`（URLは引数）

例:
- `python -m pico_hid.pc.pico_hid_macros restart_unified_api`
- `python -m pico_hid.pc.pico_hid_macros open_nanokvm --args "{\"nanokvm_url\":\"http://192.168.0.10\"}"`

## 4) 電源制御（どれか1つは欲しい）

- スマートプラグ: 強制電源断→復帰（ファイル破損リスクあり）
- ATX制御: 電源スイッチ相当を制御（安全度高め）
- 可能なら: BIOSで「AC復帰時に自動電源ON」を有効化

## 5) セキュリティ（最低限）

- NanoKVMは外部公開しない（VPN/Tailscale経由を推奨）
- Picoのマクロは“破壊的操作”になり得るので、実行を限定（確認トークン/手動トリガー）
