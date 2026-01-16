# Tesseract OCR 日本語データインストール手順

## 問題
現在、Tesseract OCRに日本語データ（`jpn.traineddata`）がインストールされていないため、日本語が正しく認識されず文字化けしています。

## 解決方法

### 方法1: 自動インストールスクリプト（推奨）

1. **PowerShellを管理者として実行**
   - Windowsキーを押して「PowerShell」と入力
   - 「Windows PowerShell」を右クリック → 「管理者として実行」

2. **スクリプトを実行**
   ```powershell
   cd "C:\Users\mana4\Desktop\manaos_integrations"
   .\install_japanese_tesseract.ps1
   ```

### 方法2: 手動インストール

1. **一時ファイルをコピー**
   ```powershell
   # PowerShellを管理者として実行
   Copy-Item "C:\Users\mana4\AppData\Local\Temp\jpn.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\jpn.traineddata" -Force
   ```

2. **確認**
   ```powershell
   & "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
   ```
   `jpn` が表示されれば成功です。

### 方法3: ダウンロードから手動インストール

1. **日本語データをダウンロード**
   - URL: https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata
   - ブラウザで開いて保存

2. **ファイルをコピー**
   - ダウンロードした `jpn.traineddata` を以下にコピー:
   - `C:\Program Files\Tesseract-OCR\tessdata\jpn.traineddata`

## インストール後の確認

インストール後、以下のコマンドで確認できます：

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

出力に `jpn` が含まれていれば成功です。

## インストール後の再実行

日本語データをインストールしたら、PDF→Excel変換を再実行してください：

```bash
python pdf_to_excel_converter.py "input.pdf" "output.xlsx"
```

これで日本語が正しく認識されるようになります。
