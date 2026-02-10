# ComfyUI Manager が表示されない場合の対処

ComfyUI の画面に「Manager」ボタンや Manager タブが出てこないときの確認・対処手順です。

---

## 1. 表示場所が変わっている（ComfyUI 0.4 以降）

**ComfyUI 0.4 以降では Manager の入口が変更されています。**

- **以前:** 画面上部の「Manager」ボタン（右上など）
- **現在:** 次のいずれかで開きます
  - **プラグイン（Plugin）アイコン** をクリック
  - **メニュー（または Help）→ Manage Extensions（拡張機能の管理）**
  - 左上の **ComfyUI ロゴ（C マーク）** から「拡張機能の管理」を選択

まずは上記の場所を確認してください。デザインが変わっているため、タブやボタン名が「Manager」でない場合があります。

---

## 2. インストール状態の確認

### 2.1 フォルダがあるか

- パス: `C:\ComfyUI\custom_nodes\ComfyUI-Manager`
- ここに `ComfyUI-Manager` **フォルダ**があるか確認（名前は `ComfyUI-Manager` のままであること）。

### 2.2 無効化されていないか

過去に「Manager を一時的に止める」スクリプトを使っている場合、フォルダ名が **`ComfyUI-Manager.disabled`** になっていることがあります。

- `C:\ComfyUI\custom_nodes\ComfyUI-Manager.disabled` だけがある
  → 有効化するにはフォルダ名を `ComfyUI-Manager` に戻します。

  ```powershell
  Rename-Item -Path "C:\ComfyUI\custom_nodes\ComfyUI-Manager.disabled" -NewName "ComfyUI-Manager"
  ```

  このワークスペースには `enable_comfyui_manager.ps1` もあるので、同じ作業をしたい場合はそれを実行しても構いません。

### 2.3 __init__.py があるか

- `C:\ComfyUI\custom_nodes\ComfyUI-Manager\__init__.py` が存在するか確認してください。ないとカスタムノードとして認識されません。

---

## 3. 依存関係と再起動

- ComfyUI-Manager のフォルダ内に `requirements.txt` がある場合:
  ```powershell
  cd C:\ComfyUI\custom_nodes\ComfyUI-Manager
  pip install -r requirements.txt
  ```
- インストールまたは名前変更のあとは **ComfyUI を完全に終了してから再起動**してください。

---

## 4. ポータブル版・特殊なビルドの場合

- 起動オプションで **`--enable-manager`** が必要な場合があります。
  使用している起動バッチやコマンドにこのオプションを追加して再起動してみてください。
- Manager 用に別の `manager_requirements.txt` がある場合は、そのディレクトリで:
  ```powershell
  pip install -r manager_requirements.txt
  ```

---

## 5. まだ出ない場合

- ComfyUI を**ターミナル（コマンドプロンプトや PowerShell）から**起動し、起動時のログに
  `ComfyUI-Manager` や `Manager` に関する **エラー** が出ていないか確認してください。
- エラーがあれば、そのメッセージに従って不足パッケージのインストールやパスの修正を行ってください。

---

## まとめチェックリスト

| 確認項目 | 対応 |
|----------|------|
| プラグインアイコン / メニュー「Manage Extensions」を探した | 新しいUIの場所を確認 |
| `custom_nodes\ComfyUI-Manager` が存在する | なければ git clone でインストール |
| `ComfyUI-Manager.disabled` になっていない | リネームして `ComfyUI-Manager` に戻す |
| `__init__.py` がある | 不足なら再 clone または再取得 |
| `requirements.txt` をインストールした | pip install -r requirements.txt |
| ComfyUI を再起動した | 終了後に起動し直す |
| ポータブル版など | `--enable-manager` の有無を確認 |

上記を試しても表示されない場合は、起動ログのエラー内容を手がかりに調査するとよいです。
