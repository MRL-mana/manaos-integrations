# PDFからExcelへの変換ツール

Google DriveからPDFをダウンロードしてExcelに変換するツールです。

## 機能

- ✅ Google DriveからPDFを自動ダウンロード
- ✅ PDFからテーブルを抽出してExcelに変換
- ✅ PDFからテキストを抽出してExcelに変換
- ✅ AIベースOCR対応（Amazon Textract、Google Cloud Vision、Microsoft Azure）
- ✅ 画像ベースPDFにも対応（OCR機能）

## 使用方法

### 基本的な使用方法

```bash
# Google Drive URLから変換
python pdf_to_excel_converter.py "https://drive.google.com/file/d/..." "output.xlsx"

# ローカルPDFファイルから変換
python pdf_to_excel_converter.py "file.pdf" "output.xlsx"
```

## OCR機能のセットアップ

### 1. Tesseract OCR（推奨・無料）

**Windows:**
1. [Tesseract OCR Windows版](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラーをダウンロード
2. インストール時に「PATHに追加」オプションを有効にする
3. PowerShellを再起動

**または、Chocolateyを使用:**
```powershell
choco install tesseract
```

**確認:**
```bash
tesseract --version
```

### 2. Amazon Textract（AIベース・高精度）

AWS認証情報を設定:
```bash
# 環境変数で設定
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
$env:AWS_REGION="ap-northeast-1"
```

### 3. Google Cloud Vision API（AIベース・高精度）

```bash
# 認証情報ファイルを設定
$env:GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

### 4. Microsoft Azure Computer Vision（AIベース・高精度）

```bash
$env:AZURE_VISION_ENDPOINT="https://your-endpoint.cognitiveservices.azure.com/"
$env:AZURE_VISION_KEY="your-api-key"
```

## OCRプロバイダーの優先順位

1. **Amazon Textract** - AIベース、最高精度
2. **Google Cloud Vision** - AIベース、高精度
3. **Microsoft Azure** - AIベース、高精度
4. **Tesseract** - 無料、ローカル実行

利用可能なプロバイダーが自動的に選択されます。

## 必要なライブラリ

```bash
pip install pandas openpyxl pdfplumber pymupdf pytesseract pillow
```

## トラブルシューティング

### Tesseractが見つからない

- Tesseractがインストールされているか確認: `tesseract --version`
- PATHに追加されているか確認
- PowerShellを再起動

### Amazon Textractエラー

- AWS認証情報が設定されているか確認
- リージョンが設定されているか確認: `$env:AWS_REGION="ap-northeast-1"`

### PDFからテキストが抽出できない

- PDFが画像ベースの可能性があります
- OCR機能を有効にしてください（Tesseractをインストール）

## 出力形式

- **テーブルが見つかった場合**: 各テーブルが別のシートに保存されます
- **テキストのみの場合**: テキストが1つのシートに保存されます
- **抽出できない場合**: 情報メッセージがシートに保存されます
