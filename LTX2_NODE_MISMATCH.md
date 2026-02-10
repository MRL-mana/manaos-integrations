# LTX-2 ワークフローとノードの不一致について

## 状況

`LTX-2_I2V_Distilled_wLora.json` などの example_workflows は、次のノードを参照しています。

- **LTXVSeparateAVLatent**
- **LTXVAudioVAEDecode**
- **LTXVEmptyLatentAudio**
- **LTXVLatentUpsampler**
- **LTXVConcatAVLatent**
- **LTXVImgToVideoInplace**
- **CM_FloatToInt**（コア／他拡張）
- **LTXVAudioVAELoader**

ComfyUI の「不足ノード」ダイアログでは、これらが**どのバージョンのコアノードだったか**が表示されます。

| バージョン | ノード例 |
|------------|----------|
| **0.7.0** | LTXVImgToVideoInplace, LTXVLatentUpsampler |
| **0.5.1** | LTXVConcatAVLatent, LTXVSeparateAVLatent |
| **0.3.64** | LTXVAudioVAEDecode, LTXVAudioVAELoader, LTXVEmptyLatentAudio |

多くは **サブグラフ 'Samplers'** 内で使われています。現在の **ComfyUI-LTXVideo**（master）のソースには、これらのノード名の定義がありません。

- ComfyUI 本体: `LTXVSeparateAVLatent` 等の定義なし（`CreateVideo` / `SaveVideo` は `comfy_extras/nodes_video.py` にあり）
- ComfyUI-LTXVideo: 上記ノードは過去のリファクタで削除または別名化された可能性
- **補足:** GitHub のこのリポジトリの履歴を検索しても `LTXVSeparateAVLatent` / `LTXVConcatAVLatent` の定義は見つかりません。ダイアログの「0.7.0 のコアノード」等のバージョンは **ComfyUI Manager が管理する拡張バージョン**の可能性が高く、**ComfyUI Manager で ComfyUI-LTXVideo のバージョン（0.7.0 等）を切り替える**のが現実的な対処です。

そのため、**現状の組み合わせでは「node LTXVSeparateAVLatent does not exist」が解消できません。**

## 実施したこと

1. **ComfyUI-LTXVideo の履歴確認**
   - `36fdaf5` (2025-07-16) にチェックアウトして確認 → `LTXVLatentUpsampler` は存在するが、`LTXVSeparateAVLatent` 等はソースに存在しなかった
   - `e1d2cff` (2026-01-06) で example_workflows（I2V/T2V）が追加されたが、同じコミットで `latent_upsampler.py` 等は削除されている
2. **ComfyUI 本体の検索**
   - `LTXVSeparateAVLatent`, `LTXVAudioVAEDecode`, `LTXVEmptyLatentAudio`, `LTXVConcatAVLatent` は ComfyUI の `comfy` / `comfy_extras` 内にも見つからず
3. **master へ戻して gemma パッチのみ再適用**
   - `patch_ltxv_gemma_encoder.py` で `model_root` 修正は再適用済み（Gemma「Unrecognized model」対策は有効な状態）

## 今後の対処案

1. **ComfyUI-LTXVideo の Issue / ディスカッションを確認**
   - GitHub: https://github.com/Lightricks/ComfyUI-LTXVideo/issues
   - 検索例: [LTXVSeparateAVLatent does not exist](https://github.com/Lightricks/ComfyUI-LTXVideo/issues?q=LTXVSeparateAVLatent) で公式の見解や互換ワークフローの有無を確認する。
2. **ComfyUI / ComfyUI-LTXVideo のアップデート**
   - 今後、上記ノードが再度追加される、または **別名のノードで同じワークフローが動く** バージョンが公開される可能性があるため、更新履歴を追う。
3. **別ワークフローの利用**
   - 現在のノード構成（`LTXVSelectLatents`, `LTXVAddLatents`, `LTXVImgToVideo` 等）だけで組めるワークフローが公式やコミュニティで共有されていれば、それを Load → Export (API) して `run_ltx2_generate.py` で実行する。

現時点では、**「LTXVSeparateAVLatent does not exist」をコード側で解消するためのコミットやパッチは見つかっておらず、環境を元に戻したうえで、上記のいずれかの方法で対応する必要があります。**

---

## 一括診断（推奨）

ComfyUI を起動した状態で、次の PowerShell を実行すると接続チェック・ノード一覧・互換ワークフロー検出を一括で行います。

```powershell
.\run_ltx2_diagnose.ps1
# 別ホストの ComfyUI の場合
.\run_ltx2_diagnose.ps1 -ComfyUrl "http://192.168.1.10:8188"
```

不足ノードがある場合、**ノードが存在したコミットを探す**には:

```powershell
.\find_ltxv_node_commit.ps1
# ComfyUI-LTXVideo のパスが違う場合
.\find_ltxv_node_commit.ps1 -LtxVideoPath "D:\ComfyUI\custom_nodes\ComfyUI-LTXVideo"
```

該当コミットが表示されたら、そのコミットに `git checkout <hash>` で合わせると example ワークフローが動く可能性があります（未検証）。

---

## すぐに試せる手順（ComfyUI 起動中）

1. **利用可能なノードを確認**
   ```powershell
   python ltx2_list_available_nodes.py
   ```
   LTX/動画関連で現在インストールされているノード名だけが表示されます。

2. **互換ワークフローを自動検出**
   ```powershell
   python ltx2_find_compatible_workflow.py "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows"
   ```
   上記フォルダ内の JSON のうち、現在の ComfyUI に存在するノードだけを使っているワークフローが「互換」として表示されます。1件でもあれば、そのファイルを ComfyUI で開き **File → Export (API)** で保存し、`run_ltx2_generate.py --workflow 保存したファイル` で実行できます。

3. **互換が0件の場合（＝ダイアログで「不足ノード」が出る場合）**
   - **ComfyUI Manager でバージョン切り替え:**
     ダイアログに「**0.7.0 のコアノード**」「**0.5.1 のコアノード**」等と出ている番号は、**ComfyUI Manager が管理する拡張バージョン**の可能性があります。
     **Manager の場所:** ComfyUI 0.4 以降では表示場所が変更されています。**プラグイン（Plugin）アイコン**をクリックするか、**メニュー（Help）→ Manage Extensions（拡張機能の管理）**、または左上の **C マーク（ComfyUI ロゴ）** から「拡張機能の管理」を開いてください。詳細は `COMFYUI_MANAGER_NOT_SHOWING.md` を参照。
     Manager を開いたら **ComfyUI-LTXVideo** を探し、「バージョン」や「更新」から **0.7.0 相当**が選べるか確認してください。選べればそのバージョンに切り替えてから ComfyUI を再起動し、再度ワークフローを Load します。
     ※ Manager がどこにも見当たらない場合は、`COMFYUI_MANAGER_NOT_SHOWING.md` の手順でインストール・無効化解除・再起動を確認してください。未インストールの場合は `custom_nodes` に `git clone https://github.com/ltdrdata/ComfyUI-Manager.git` で入れ、ComfyUI を再起動してください。
   - **git でノードが存在したコミットに合わせる:**
     ```powershell
     .\find_ltxv_node_commit.ps1
     ```
     表示されたコミットに `git checkout <hash>` で合わせてから ComfyUI を再起動し、再度ワークフローを Load してみてください。
   - 手動で探す例:
     ```bash
     cd C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo
     git log -p -S "LTXVSeparateAVLatent" -- "*.py"
     ```
     該当コミットがあれば、そのコミットに合わせることで example ワークフローが動く可能性があります（動作は未検証）。
