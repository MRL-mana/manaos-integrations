# LM Studio モデル読み込み問題の解決ガイド

## 問題の原因

エラーメッセージから、以下の問題が考えられます：

```
Failed to load model "qwen2.5-coder-32b-instruct". 
Error: Failed to load LLM engine from path: 
C:\Users\mana4\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-1.103.0\llm_engine_c
```

### 考えられる原因

1. **バックエンドエンジン（llama.cpp）の問題**
   - バックエンドエンジンのパスが見つからない
   - バックエンドエンジンが破損している
   - バックエンドエンジンが正しくインストールされていない

2. **モデルファイルの問題**
   - モデルファイルが破損している
   - モデルファイルのパスが正しくない

3. **GPU/CUDAの問題**
   - NVIDIAドライバーが古い
   - CUDAが正しくインストールされていない
   - GPUメモリが不足している

4. **LM Studioの設定問題**
   - JITロードが無効になっている
   - バックエンドの設定が正しくない

## 解決方法（優先順位順）

### 方法1: LM Studioを再起動（最も簡単）

1. **LM Studioを完全に終了**
   - タスクマネージャーで`LM Studio`プロセスを確認
   - すべてのプロセスを終了

2. **LM Studioを再起動**

3. **サーバーを起動**
   - 「Server」タブで「Start Server」をクリック

4. **モデルをロード**
   - 「Chat」タブでモデルを選択して「Load」をクリック

### 方法2: LM Studioの設定を確認

1. **「Settings」を開く**

2. **「Backend」タブを確認**
   - バックエンドが正しく選択されているか確認
   - 必要に応じて別のバックエンドを選択

3. **「Model」タブを確認**
   - モデルのパスが正しいか確認
   - JITロードが有効になっているか確認

### 方法3: モデルを再ダウンロード

1. **LM Studioでモデルを削除**
   - 「Local Models」タブでモデルを右クリック
   - 「Delete」を選択

2. **モデルを再ダウンロード**
   - 「Search」タブでモデルを検索
   - ダウンロードを実行

### 方法4: LM Studioを更新

1. **LM Studioのバージョンを確認**
   - 「Help」→「About」でバージョンを確認

2. **最新版に更新**
   - LM Studioの公式サイトから最新版をダウンロード
   - インストール（既存の設定は保持される）

### 方法5: LM Studioを再インストール（最終手段）

1. **LM Studioをアンロード**
   - Windowsの「アプリと機能」からLM Studioを削除

2. **設定ファイルを削除（オプション）**
   - `C:\Users\mana4\.lmstudio` を削除（モデルも削除される）

3. **LM Studioを再インストール**

4. **モデルを再ダウンロード**

## 診断ツールの実行

問題を特定するために、診断ツールを実行してください：

```powershell
python diagnose_lm_studio.py
```

このツールは以下を確認します：
- LM Studioサーバーの状態
- モデルファイルの存在
- バックエンドエンジンの状態
- JITロードの動作

## 一時的な回避策

モデルがロードできない場合、以下の回避策があります：

### 回避策1: より小さなモデルを使用

32Bモデルの代わりに、より小さなモデル（7Bや14B）を試してください：

```python
# excel_llm_ocr_corrector.py で使用するモデルを変更
llm_model = "qwen2.5-coder-7b-instruct"  # 32Bの代わりに7B
```

### 回避策2: Ollamaにフォールバック

LM Studioが使用できない場合、Ollamaにフォールバックします：

```powershell
# USE_LM_STUDIOを無効化
$env:USE_LM_STUDIO="0"
python excel_llm_ultra_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ULTRA.xlsx --passes 3 --verbose
```

## 確認方法

モデルが正しくロードされたか確認：

```powershell
python check_lm_studio_loaded.py
```

「✓ ロード済み・使用可能」と表示されればOKです。
