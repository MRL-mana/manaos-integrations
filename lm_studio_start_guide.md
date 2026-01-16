# LM Studio 起動・活用ガイド

## 現在の状況

✗ **LM Studioサーバーが起動していません**

エラー: `接続できませんでした (WinError 10061)`

## 解決方法（3ステップ）

### ステップ1: LM Studioを起動

1. **LM Studioアプリケーションを起動**
   - デスクトップまたはスタートメニューから起動

2. **LM Studioが完全に起動するまで待つ**
   - ウィンドウが表示され、モデル一覧が読み込まれるまで待つ

### ステップ2: サーバーを開始

1. **「Server」タブを開く**
   - LM Studioの上部タブから「Server」を選択

2. **「Start Server」をクリック**
   - サーバーが起動すると、緑色のインジケーターが表示されます
   - ポート番号（通常は1234）が表示されます

3. **サーバーが起動したことを確認**
   - 「Server is running on port 1234」などのメッセージが表示されます

### ステップ3: モデルをロード（オプション）

**注意**: モデルを事前にロードしなくても、JITロード（推論時に自動ロード）が有効になっていれば動作します。

ただし、初回の推論が遅くなる可能性があります。

1. **「Chat」タブを開く**
2. **モデルを選択**
   - 推奨: `qwen2.5-coder-32b-instruct` または `ggml-org/qwen2.5-coder-14b-instruct`
3. **「Load」をクリック**（オプション）
   - 事前にロードすると、初回推論が速くなります

## 確認方法

サーバーが起動したか確認：

```powershell
python check_lm_studio_loaded.py
```

または：

```powershell
python test_lm_studio_simple.py
```

「✓ 成功！」と表示されればOKです。

## 活用方法

### 1. LLM修正処理を実行

```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_ultra_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ULTRA.xlsx --passes 3 --verbose
```

### 2. アンサンブル修正を実行

```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_ensemble_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ENSEMBLE.xlsx
```

### 3. 複数回修正を実行

```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_multi_pass_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_MULTIPASS.xlsx --passes 3
```

## トラブルシューティング

### 問題1: サーバーが起動しない

- LM Studioを再起動
- ポート1234が他のアプリケーションで使用されていないか確認
- ファイアウォールの設定を確認

### 問題2: モデルがロードできない

- バックエンドをCPU版に変更（`lm_studio_quick_fix.md`を参照）
- LM Studioを再起動
- モデルを再ダウンロード

### 問題3: 接続エラー

- LM Studioの「Server」タブでサーバーが起動しているか確認
- `http://localhost:1234/v1/models` にブラウザでアクセスして確認

## 期待される効果

LM Studioを使用すると：
- ✅ ローカルLLMで高速処理（GPU使用時）
- ✅ より高い精度の修正（大きなモデル使用時）
- ✅ プライバシー保護（データが外部に送信されない）
