# Excel/CSV → LLM処理の使用例

# 基本的な使用方法
python excel_llm_processor.py data.xlsx

# タスクを指定
python excel_llm_processor.py data.xlsx "集計分析"
python excel_llm_processor.py data.xlsx "ミス検出"
python excel_llm_processor.py data.xlsx "傾向分析"

# CSVファイルも対応
python excel_llm_processor.py data.csv "異常値検出"
