# Pico 2 W HID - ローカルLLM / Cursor からマウス・キーボード操作

Raspberry Pi Pico 2 W を USB HID（マウス・キーボード）として動かし、**母艦のローカルLLMや Cursor の MCP ツール**から操作するための構成です。

## 構成

- **Pico 2 W**: CircuitPython で動作。USB シリアルでコマンドを受信し、HID でマウス・キーボードを操作。
- **母艦**: `pico_hid_client.py` でシリアル送信。MCP サーバー経由で Cursor / ローカルLLM からツール呼び出し可能。

## 1. Pico 2 W のセットアップ

### 1.1 CircuitPython を入れる

1. [CircuitPython - Raspberry Pi Pico 2 W](https://circuitpython.org/board/raspberry_pi_pico2_w/) から UF2 をダウンロード。
2. Pico 2 W を **BOOTSEL 長押ししながら USB 接続**し、出てきたドライブに UF2 をコピー。自動で再起動し、`CIRCUITPY` ドライブになります。

### 1.2 ライブラリをコピー

[CircuitPython Bundle](https://circuitpython.org/libraries) の「Bundle for 10.x」をダウンロードし、解凍して次のフォルダを `CIRCUITPY` の `lib` にコピーします。

- `adafruit_hid`（フォルダごと）

### 1.3 code.py をコピー

このリポジトリの `pico_hid/circuitpython/code.py` を、Pico の `CIRCUITPY` ドライブのルートに `code.py` としてコピーします。

### 1.4 シリアルポートの確認

CircuitPython では **CDC（シリアル）** と **HID（キーボード・マウス）** が同時に有効です。母艦の「デバイスの管理」や `pico_hid_client.get_serial_ports()` で、Pico 用の COM ポートを確認してください。

## 2. 母艦のセットアップ

```bash
pip install pyserial pynput pyautogui
```

**デフォルトで PC 側（pynput）で操作**するため、環境変数なしでそのまま動きます。

ワークスペースのルートで:

```bash
python -m pico_hid.pc.pico_hid_client
```

何も引数なしで実行すると使い方が出ます。例:

```bash
python -m pico_hid.pc.pico_hid_client m 10 0       # マウス相対移動
python -m pico_hid.pc.pico_hid_client ma 100 200  # 絶対座標へ移動（PC のみ）
python -m pico_hid.pc.pico_hid_client ca 50 50    # (50,50) をクリック（PC のみ）
python -m pico_hid.pc.pico_hid_client c left      # 左クリック
python -m pico_hid.pc.pico_hid_client k ENTER     # Enter キー
python -m pico_hid.pc.pico_hid_client combo ctrl c  # Ctrl+C（PC のみ）
python -m pico_hid.pc.pico_hid_client t hello     # "hello" と入力
python -m pico_hid.pc.pico_hid_client w -1        # ホイール下
python -m pico_hid.pc.pico_hid_client pos         # マウス座標表示（PC のみ）
python -m pico_hid.pc.pico_hid_client screen      # スクリーンショット（PC のみ）
```

## 3. Cursor / ローカルLLM から使う（MCP）

ManaOS 統合 MCP サーバーに次のツールが入っています。デフォルトで **PC 側（pynput）** で操作するため、そのまま使えます。

| ツール名 | 説明 |
|----------|------|
| `pico_hid_mouse_move` | マウスを相対移動（dx, dy） |
| `pico_hid_mouse_move_absolute` | 絶対座標 (x, y) に移動（PC のみ） |
| `pico_hid_mouse_click` | マウスクリック（left / right / middle） |
| `pico_hid_mouse_click_at` | 指定座標 (x, y) をクリック（PC のみ） |
| `pico_hid_key_press` | キー送信（A, ENTER, TAB, SPACE など） |
| `pico_hid_key_combo` | キーコンボ（例: ["ctrl", "c"] で Ctrl+C）（PC のみ） |
| `pico_hid_type_text` | 文字列をそのまま入力 |
| `pico_hid_scroll` | ホイールスクロール（delta: 正=上, 負=下） |
| `pico_hid_mouse_position` | 現在のマウス座標を取得（PC のみ） |
| `pico_hid_screen_size` | 画面サイズ（幅, 高さ）を取得（PC のみ） |
| `pico_hid_screenshot` | 画面をキャプチャして PNG 保存（PC のみ） |
| **`pico_hid_type_text_auto`** | **［全自動］IME切替→入力→スクショまで一括。内容確認し OK なら Enter 2回。間違いなら打ち直しへ** |
| **`pico_hid_clear_and_retype_auto`** | **［打ち直し］Ctrl+A→Delete でクリア後、再度 IME切替→入力→スクショ。確認して OK なら Enter 2回** |
| **`pico_hid_click_then_type_auto`** | **［入力場所を指定］(x,y) をクリックしてから入力→スクショ。入力欄は事前にスクショで確認** |

Cursor やローカルLLM から「マウスを動かして」「この文字を打って」といった指示を出すと、これらのツールが呼ばれます。**推奨フロー（入力場所の確認＋マウス操作）**：1) `pico_hid_screenshot` で画面を撮り、入力欄の位置を確認 2) `pico_hid_click_then_type_auto(x, y, text)` でその座標をクリック→入力→スクショ 3) スクショで内容確認→誤りなら `pico_hid_clear_and_retype_auto` で打ち直し 4) OK なら Enter 2回。

## 4. シリアルプロトコル（参考）

1 行 1 コマンド、改行で終端です。

- `m,dx,dy` — マウス移動
- `c,left` / `c,right` / `c,middle` — クリック
- `w,delta` — ホイール
- `k,KEY` — キー（KEY: A–Z, ENTER, TAB など）
- `t,文字列` — 文字列入力（改行までがペイロード）

## トラブルシュート

- **COM ポートが見つからない**: CircuitPython で CDC が有効か確認。別のシリアルターミナルで Pico を開いていないか確認。
- **HID が動かない**: `code.py` と `lib/adafruit_hid` が正しくコピーされているか確認。REPL で `import usb_hid` が通るか確認。
- **MCP で「Pico に送信できません」**: 母艦で `python -c "from pico_hid.pc.pico_hid_client import find_pico_port; print(find_pico_port())"` でポートが取れているか確認。
