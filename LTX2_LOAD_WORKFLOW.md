# ComfyUI でワークフローを Load する手順

**いちばん迷わない方法**: 下の「方法1: ドラッグ＆ドロップ」で、**真ん中の黒いキャンバス**に JSON ファイルをドラッグするだけです。

---

## やり方（2通り）

### 方法1: ドラッグ＆ドロップ（いちばん簡単）

1. **エクスプローラーでワークフローファイルがあるフォルダを開く**
   - フォルダを開く: プロジェクトで `.\open_ltx2_workflow_folder.ps1` を実行するか、手動で次を開く
     `C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows`
   - 中にある **`LTX-2_I2V_Distilled_wLora.json`** を探す。

2. **ComfyUI の画面を開く**
   - ブラウザで **http://127.0.0.1:8188** を開く（ComfyUI が起動していること）。

3. **ファイルをキャンバスにドラッグ**
   - エクスプローラーで **`LTX-2_I2V_Distilled_wLora.json`** を**左クリックで押さえたまま**、ブラウザの ComfyUI の**ノードが並んでいるグレーっぽいエリア（キャンバス）**まで持っていく。
   - そのエリアの上で**マウスを離す**（ドロップする）。
   - ワークフローが読み込まれる。

---

### 方法2: Load ボタンから開く

1. ブラウザで **http://127.0.0.1:8188** を開く。

2. **Load の出し方**（この ComfyUI の画面の場合）:
   - **左上のワークフロー名「Unsaved Workflow (3)」の横の ▼** をクリック → メニューに **「Load」** や **「Open」** があればそれを選ぶ。
   - または **右上の「…」（三点リーダー）** をクリック → **「Load」** や **「File」→「Load」** を探す。
   - または **左サイドバーの「書類／ファイル」のようなアイコン**（下から2番目あたり）をクリック → ワークフロー読み込みの項目を探す。
   - どれかで「ワークフローを読み込む」ダイアログが出ます。

3. **ファイル選択のダイアログ**が開いたら、次のファイルを選ぶ:
   ```
   C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\LTX-2_I2V_Distilled_wLora.json
   ```
   - ダイアログで `ComfyUI` → `custom_nodes` → `ComfyUI-LTXVideo` → `example_workflows` とたどり、**LTX-2_I2V_Distilled_wLora.json** を選んで「開く」。

4. ワークフローが読み込まれる。

---

## Load のあと（Export (API) するまで）

1. ワークフローが表示されたら、メニューから **「File」→「Export (API)」** を選ぶ（または Export / Save API のような項目）。
2. 保存先を **`ltx2_workflows`** フォルダにして、ファイル名を **`ltx2_i2v_from_ui.json`** にして保存。
3. その後、プロジェクトで:
   ```powershell
   python ltx2_patch_workflow.py ltx2_workflows/ltx2_i2v_from_ui.json ltx2_workflows/ltx2_i2v_ready.json
   python run_ltx2_generate.py --workflow ltx2_workflows/ltx2_i2v_ready.json --prompt "your prompt"
   ```

---

## フォルダをすぐ開きたいとき

**どこからでも使える方法**（PowerShell で）:

```powershell
explorer "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows"
```

これでワークフローファイルがあるフォルダがエクスプローラーで開きます。
その中の **LTX-2_I2V_Distilled_wLora.json** を ComfyUI のキャンバスにドラッグすれば Load できます。

---

**プロジェクトフォルダにいる場合**（`C:\Users\mana4\Desktop\manaos_integrations` に cd したあと）:

```powershell
.\open_ltx2_workflow_folder.ps1
```

でも同じフォルダが開きます。
