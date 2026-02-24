# 🚀 ComfyUI Qwen-Image-2512 ワークフロー セットアップガイド

## クイックスタート（5分）

### 前提条件チェック
```powershell
# ComfyUI サーバーが起動している
curl http://localhost:8188/api/

# LM Studio ローカルサーバーが起動している
curl http://localhost:1234/v1/models
```

### ワークフロー取り込み手順

#### 方法 A: ComfyUI Web UI で直接インポート (推奨)

1. ComfyUI Web UI を開く (`http://localhost:8188`)
2. **Load** → ワークフロー JSON ファイルを選択
   - 取得ワークフロー：
     - `comfyui_workflows/05_wQween-2512-Real-Random2.json` (Anima→Qwen i2i)
     - `comfyui_workflows/07_Qwen-2512-real-random.json` (Anime→Real batch)
     - `comfyui_workflows/05_wAnima_preview-Random.json` (Real→Anime batch)
     - `comfyui_workflows/FLUX1_real2.json` (Flux base)
     - `comfyui_workflows/Qwen-image_2512.json` (Qwen final)

#### 方法 B: コマンドラインでワークフロー配置

```powershell
# ComfyUI がシンボリックリンクの場合（外部インストール）
$comfyui_root = "D:\ComfyUI"  # 実際のパスに変更
$workflows_src = "C:\Users\mana4\Desktop\manaos_integrations\comfyui_workflows"

# ワークフロー用フォルダが存在しなければ作成
if(-not (Test-Path "$comfyui_root\workflows")) {
    New-Item -ItemType Directory "$comfyui_root\workflows" -Force
}

# リポジトリのワークフロー JSON をコピー
Copy-Item "$workflows_src\*.json" "$comfyui_root\workflows\" -Force

# 確認
ls "$comfyui_root\workflows\*.json" | Select Name,Length
```

---

## ワークフロー運用ガイド

### Variant A: Anima イラスト → Qwen i2i 高品質化（34.8 KB）

**用途**：高品質なアニメイラストを、さらに精密な実写的画像に変換

**必須モデル**：
- Qwen-Image-2512 (ComfyUI)
- Qwen3-VL-4B (LM Studio Image-to-Text)

**入力**: Anima モデルで生成したイラスト（または任意の高品質イラスト）  
**プロセス**:
1. イラストを読み込み
2. LM Studio で描写を詳細に解析・抽出
3. 抽出プロンプトをブラッシュアップ（Text-to-Text）
4. Qwen Image 2512 で最終生成

**実行例**：
```powershell
# ComfyUI Web UI にワークフローをロード
# 入力画像フォルダを指定
# Queue ボタンを押す
# 約 3-5 分で完成
```

---

### Variant B: アニメフォルダ → 一括リアル化（25.5 KB）

**用途**：大量のアニメイラストを自動でリアルな画像に一括変換

**必須モデル**：
- Qwen-Image-2512
- Qwen3-VL-4B (LM Studio)
- Was Node Suite（`Load Image Batch` ノード）

**入力**: アニメ画像フォルダ  
**プロセス**:
1. `Load Image Batch` で複数画像を自動読み込み
2. 各画像を LM Studio で分析
3. 自動プロンプト生成
4. Qwen Image 2512 で生成

**実行例**：
```powershell
# 入力フォルダにアニメ画像を100枚配置
# ワークフローの "Load Image Batch" ノードで
# フォルダパスと回数（100）を指定
# Queue でバッチ実行開始
# 処理中は自動で次々と処理
```

---

### Variant C: リアル美女 → アニメ化バッチ（28.9 KB）

**用途**：生成されたリアル美女画像をアニメイラストに逆変換

**必須モデル**：
- Anima-preview
- Qwen3-VL-4B (LM Studio)
- Was Node Suite

**入力**: リアル画像フォルダ  
**プロセス**：
1. Load Image Batch でリアル画像を一括読み込み
2. LM Studio で実写特徴を抽出（Image-to-Text）
3. アニメ用プロンプトに最適化（Text-to-Text）
4. Anima-preview で高精細アニメ出力

---

### Variant D: Flux → LM Studio → Qwen 3-Stage パイプライン（8.8 KB + 27.1 KB）

**用途**：ランダム生成から最終高品質化までの完全パイプライン

**必須モデル**：
- Flux.1 schnell
- SD1.5 系（途中段階）
- Qwen-Image-2512
- Qwen3-VL-4B

**プロセス**:
1. 簡単なテキストプロンプトを Flux で生成（短時間）
2. 出力画像を LM Studio で分析・詳細化
3. SD1.5 で中間リファイン
4. 再度 LM Studio で最終プロンプト最適化
5. Qwen Image 2512 で究極の実写生成

**特徴**：
- Flux でランダムガチャ可能
- SD1.5 は短時間で繰り返し実行可
- 最終 Qwen 出力で超高品質実現

---

## 依存関係チェック

### ComfyUI カスタムノード
```bash
# Was Node Suite（バッチ処理必須）
git clone https://github.com/wassname/ComfyUI_Wassname_nodes

# LM Studio Nodes for ComfyUI（LM Studio 連携必須）
git clone https://github.com/aiaicreate/LM-Studio-Nodes-ComfyUI
```

### LM Studio セットアップ
```
1. LM Studio を起動
2. Developer タブから "Start Local Server" を有効化
3. モデルロード：Qwen3-VL-4B
4. デフォルトポート: http://localhost:1234
```

### ComfyUI ノード確認
```powershell
# ComfyUI Web UI → メニュー → Node Search
# 検索キーワード：
#   - "Load Image Batch" (Was Node Suite)
#   - "LM Studio" (LM Studio Nodes)
#   - "Qwen" (ComfyUI Qwen node)
#   - "FLUX" (Flux model nodes)
```

---

## トラブルシューティング

### エラー: "Load Image Batch not found"
```powershell
# Was Node Suite をインストール
cd ComfyUI/custom_nodes
git clone https://github.com/wassname/ComfyUI_Wassname_nodes
# ComfyUI を再起動
```

### エラー: "LM Studio connection failed"
```powershell
# LM Studio サーバーが起動しているか確認
curl http://localhost:1234/v1/models

# ポート1234が他のプロセスで使用されていないか確認
netstat -ano | findstr ":1234"
```

### エラー: "Qwen-Image-2512 model not found"
```powershell
# モデルダウンロード
cd ComfyUI_root
pwsh -NoProfile -ExecutionPolicy Bypass -File C:\Users\mana4\Desktop\manaos_integrations\install_qwan_image_2512.ps1
```

---

## 推奨実行順序

### 初回セットアップ（30分）
1. ✅ ComfyUI が起動 & Web UI アクセス可能
2. ✅ LM Studio が起動 & サーバー ON
3. ✅ Was Node Suite インストール
4. ✅ LM Studio Nodes for ComfyUI インストール
5. ✅ Qwen3-VL-4B モデルを LM Studio にロード
6. ✅ Qwen-Image-2512 モデルを ComfyUI にダウンロード

### 運用フロー（推奨）
1. **高品質実写が欲しい** → Variant A or D
2. **大量のアニメを処理** → Variant B or C
3. **カスタマイズ重視** → Variant D (Flux ランダム + トリミング + 最終)

---

## パフォーマンス目安（NVIDIA RTX 4060 Ti 8GB）

| Variant | 処理時間 | メモリ使用量 | 出力品質 |
|---------|----------|------------|--------|
| A (i2i Qwen) | 2-3分 | 6-7GB | ⭐⭐⭐⭐⭐ |
| B (Anime→Real) | 2分/枚 | 6-7GB | ⭐⭐⭐⭐⭐ |
| C (Real→Anime) | 2分/枚 | 6-7GB | ⭐⭐⭐⭐⭐ |
| D (Flux→Qwen) | 5-7分 | 7-8GB | ⭐⭐⭐⭐⭐ |

---

## 統合検証スクリプト

```powershell
# manaos_integrations リポジトリのセットアップ検証
pwsh -NoProfile -ExecutionPolicy Bypass -File .\validate_qwen_setup.ps1
```

---

**最終更新**: 2026-02-24  
**ワークフロー取得元**: note.com / Yasu_aiart (prime_squid6206)
