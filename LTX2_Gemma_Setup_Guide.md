# LTX-2 Gemmaモデルセットアップガイド

## 現在の状況

認証プロセスで全角文字が受け付けられない問題が発生しています。

## 解決方法

### 方法1: 新しいコマンドを使用（推奨）

```powershell
hf auth login
```

このコマンドを使用すると、全角/半角の問題を回避できます。

### 方法2: 環境変数でトークンを設定

```powershell
# トークンを取得: https://huggingface.co/settings/tokens
$env:HF_TOKEN = "your_token_here"
```

### 方法3: 手動で認証

1. ブラウザで https://huggingface.co/settings/tokens にアクセス
2. トークンを生成（Read権限でOK）
3. 以下のコマンドを実行:

```powershell
hf auth login
# または
huggingface-cli login
```

**重要**: プロンプトで「Add token as git credential? (Y/n)」と聞かれたら、**半角の 'y' または 'n'** を入力してください。全角の「ｙ」は受け付けられません。

## セットアップ手順（簡易版）

1. **アクセス申請**
   - https://huggingface.co/google/gemma-3-12b-it にアクセス
   - 「Request access」をクリック

2. **認証**
   ```powershell
   hf auth login
   ```
   または環境変数で設定:
   ```powershell
   $env:HF_TOKEN = "your_token_here"
   ```

3. **ダウンロード**
   ```powershell
   python download_ltx2_models.py
   ```

4. **確認**
   ```powershell
   python check_ltx2_models.py
   ```

## トラブルシューティング

### 全角文字エラー

`Invalid input. Must be one of ('y', 'yes', '1', 'n', 'no', '0', '')`

**解決**: 半角の 'y' または 'n' を入力してください。

### 認証が完了しない

環境変数を使用:
```powershell
$env:HF_TOKEN = "your_token_here"
python download_ltx2_models.py
```
