# VisiData クイックスタートガイド

## 概要

VisiDataは「コスパ最強のCLIエクセル」ツールです。Excelを開く前の「まず重い...」という時間を完全に削除します。

## セットアップ

### Windows（PowerShell）

```powershell
# セットアップスクリプトを実行
.\setup_visidata.ps1
```

または手動でインストール:

```powershell
py -m pip install -U visidata openpyxl
```

### Mac / Linux

```bash
python3 -m pip install -U visidata openpyxl
```

## 動作確認

```bash
vd test.xlsx
```

## 最低限キー（これだけ覚えればOK）

| キー | 機能 |
|------|------|
| `q` | 終了 |
| `/` | 検索 |
| `s` | 並べ替え（今いる列で） |
| `[` / `]` | 列移動（左/右） |
| `g` / `G` | 先頭行 / 最終行 |
| `Ctrl+F` | フィルタ |

## 便利機能

| キー | 機能 |
|------|------|
| `=` | 列の集計（合計、平均など） |
| `z-` | 列を削除 |
| `z+` | 列を追加 |
| `e` | セルを編集 |
| `Ctrl+S` | 保存 |

## 使用例

### Excelファイルを開く

```bash
vd data.xlsx
```

### CSVファイルを開く

```bash
vd data.csv
```

### 複数ファイルを開く

```bash
vd file1.xlsx file2.csv
```

## 次のステップ

### 表をLLMに渡して処理させる統合

VisiDataで見るだけで終わらせない、「表をLLMに渡して処理させる」統合も利用できます:

```powershell
# 統合セットアップ
.\setup_excel_llm_integration.ps1

# 使用例
python excel_llm_processor.py data.xlsx 異常値検出
```

この統合により、以下のワークフローが可能になります:

1. **xlsx → CSV抽出**
2. **LLMに「異常値・集計・ミス検出」を依頼**
3. **結果をSlack/Notionへ自動送信**

## マナOSとの統合

ManaOSの「トークン節約＆時短」思想に完全一致する統合です:

- ✅ ローカルLLM（Ollama）を使用
- ✅ トークンコストゼロ
- ✅ 高速処理
- ✅ 自動化可能

## トラブルシューティング

### VisiDataが起動しない

```powershell
# Python環境を確認
python --version

# 再インストール
py -m pip install --force-reinstall visidata openpyxl
```

### Excelファイルが開けない

```powershell
# openpyxlを確認
python -m pip show openpyxl

# 再インストール
py -m pip install --force-reinstall openpyxl
```

## 参考リンク

- [VisiData公式サイト](https://www.visidata.org/)
- [VisiDataドキュメント](https://www.visidata.org/docs/)
