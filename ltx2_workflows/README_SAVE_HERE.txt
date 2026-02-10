ComfyUI で File -> Export (API) したら、ここに保存してください。
ファイル名: ltx2_i2v_from_ui.json

【保存先を選べない場合】
  どこでもいいので保存（例: ダウンロードフォルダ）して、
  プロジェクトフォルダで:
    .\copy_ltx2_export.ps1 "C:\Users\mana4\Downloads\保存したファイル名.json"
  （実際のパスに置き換えてください）
  その後: .\run_ltx2_all.ps1

【「node XXX does not exist」が出る場合】
  1. プロジェクトフォルダで一括診断を実行:
       .\run_ltx2_diagnose.ps1  または  .\run_ltx2_diagnose.bat
  2. 診断結果で「互換」と出たワークフローを ComfyUI で開き、
     File -> Export (API) でこのフォルダに ltx2_i2v_from_ui.json として保存
  3. 互換が0件のときは LTX2_NODE_MISMATCH.md を参照
