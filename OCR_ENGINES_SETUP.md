# OCRエンジン追加インストール手順

日本語読み取り精度を向上させるため、以下のOCRエンジンを追加インストールできます。

## 1. EasyOCR（推奨：日本語に強い）

```bash
pip install easyocr
```

**特徴:**
- 日本語と英語の同時認識が可能
- 初回実行時にモデルを自動ダウンロード（時間がかかります）
- GPU対応（オプション）

**使用例:**
```python
from ocr_multi_provider import MultiProviderOCR
ocr = MultiProviderOCR()
result = ocr.recognize("image.png", provider="easyocr", lang=["ja", "en"])
```

## 2. PaddleOCR（最強：日本語に非常に強い）

```bash
pip install paddlepaddle paddleocr
```

**特徴:**
- 日本語認識精度が非常に高い
- 表のレイアウト認識も優秀
- 初回実行時にモデルを自動ダウンロード（時間がかかります）
- GPU対応（オプション）

**使用例:**
```python
from ocr_multi_provider import MultiProviderOCR
ocr = MultiProviderOCR()
result = ocr.recognize("image.png", provider="paddleocr", lang="japan")
```

## 優先順位

現在のシステムは以下の優先順位でOCRエンジンを選択します：

1. **PaddleOCR**（日本語に最も強い）
2. **EasyOCR**（日本語に強い）
3. **Tesseract**（標準、日本語対応）
4. AIベースOCR（認証が必要）

## 列検出の改善

以下の改善を実施しました：

- 罫線検出の閾値を下げて、より多くの列を検出
- min_gapを小さくして、細かい列も検出可能に
- 解像度に応じた自動調整

## 日本語読み取りの改善

- 複数のOCRエンジンで試行し、最良の結果を選択
- 文字数、信頼度、日本語文字の割合を考慮したスコアリング
- アンサンブル方式で空欄を埋める
