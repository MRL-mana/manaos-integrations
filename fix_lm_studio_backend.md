# LM Studio バックエンド問題の解決方法

## 問題の詳細

エラーメッセージ：
```
Failed to load LLM engine from path: 
C:\Users\mana4\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-1.103.0\llm_engine_cuda12.node. 
The specified module could not be found.
```

**原因**: LM StudioがCUDA対応バックエンドを使おうとしているが、そのモジュールファイルが見つからない

## 解決方法

### 方法1: LM Studioの設定でバックエンドを変更（推奨）

1. **LM Studioを起動**

2. **「Settings」を開く**
   - 右上の歯車アイコンをクリック

3. **「Backend」タブを開く**

4. **バックエンドを変更**
   - 現在: `llama.cpp-win-x86_64-nvidia-cuda12-avx2-1.103.0` (CUDA版)
   - 変更先: `llama.cpp-win-x86_64-avx2-1.103.0` (CPU版)
   - または: `llama.cpp-win-x86_64-avx2-1.101.0` (CPU版、古いバージョン)

5. **「Apply」または「Save」をクリック**

6. **LM Studioを再起動**

7. **モデルをロード**
   - 「Chat」タブでモデルを選択して「Load」をクリック

### 方法2: LM Studioを再起動してバックエンドを再検出

1. **LM Studioを完全に終了**
   - タスクマネージャーで`LM Studio`プロセスを確認
   - すべてのプロセスを終了

2. **LM Studioを再起動**

3. **バックエンドが自動的に再検出されるのを待つ**

4. **モデルをロード**

### 方法3: CUDA版バックエンドを修復（GPUを使用したい場合）

1. **LM Studioを完全に終了**

2. **バックエンドディレクトリを確認**
   ```
   C:\Users\mana4\.lmstudio\extensions\backends\
   ```

3. **CUDA版バックエンドを削除**
   - `llama.cpp-win-x86_64-nvidia-cuda12-avx2-1.103.0` フォルダを削除

4. **LM Studioを再起動**
   - バックエンドが自動的に再ダウンロードされる

5. **または、LM Studioを最新版に更新**
   - 最新版には正しいバックエンドが含まれている可能性がある

### 方法4: CPU版バックエンドを強制使用（一時的な回避策）

診断結果から、以下のCPU版バックエンドが利用可能です：
- `llama.cpp-win-x86_64-avx2-1.103.0`
- `llama.cpp-win-x86_64-avx2-1.101.0`
- `llama.cpp-win-x86_64-avx2-1.66.0`

これらはGPUを使用しませんが、動作します。

## 確認方法

バックエンドが正しく設定されたか確認：

```powershell
python diagnose_lm_studio.py
```

「✓ 成功！モデルがロードされました」と表示されればOKです。

## GPUを使用したい場合

CUDA版バックエンドを使用するには：

1. **NVIDIAドライバーを最新版に更新**
2. **CUDA Toolkitをインストール**（必要に応じて）
3. **LM Studioを最新版に更新**
4. **バックエンドを再インストール**

ただし、CPU版でも動作します（速度は遅いですが）。
