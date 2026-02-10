# LTX-2 動画を今すぐ生成する手順

## 状況

- ComfyUI は起動しており、LTX 用ノードは利用可能です。
- プロジェクト内の `ltx2_i2v_ready.json` 等は**旧ノード名**（LTXVSeparateAVLatent 等）のため、そのままでは送信できません。
- example_workflows の JSON は **UI 形式**（nodes/links）のため、変換＋パッチでは接続の不一致で「Prompt outputs failed validation」になります。

## 推奨: ComfyUI で Export (API) したワークフローを使う

1. **ブラウザで ComfyUI を開く**
   ```
   http://127.0.0.1:8188
   ```

2. **ワークフローを読み込む**
   - 次のフォルダを開く: `C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows`
   - **LTX-2_I2V_Distilled_wLora.json** をキャンバスに**ドラッグ＆ドロップ**
   - 「不明なノード」が出る場合 → その example は現行バージョンと不一致です。別の JSON を試すか、`.\find_ltxv_node_commit.ps1` でノードが存在したコミットに合わせてください。

3. **API 形式で保存**
   - メニュー **File → Export (API)**
   - 保存先: `C:\Users\mana4\Desktop\manaos_integrations\ltx2_workflows\ltx2_i2v_from_ui.json`
     （保存先を選べない場合は「ダウンロード」などに保存し、後で `copy_ltx2_export.ps1` でコピー）

4. **生成実行**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\run_ltx2_all.ps1 "a calm sea at sunset, gentle waves"
   ```
   または:
   ```powershell
   python run_ltx2_generate.py --workflow ltx2_workflows/ltx2_i2v_from_ui.json --prompt "a calm sea at sunset, gentle waves"
   ```

## 補足

- 手順 2 で「不明なノード」が出ない＝現在の ComfyUI のノードだけでワークフローが開けているので、Export (API) した JSON はそのまま送信できます。
- 開始画像が必要なワークフローの場合は、画像を ComfyUI の `input` フォルダに置き、`--image ファイル名.png` で指定してください。
