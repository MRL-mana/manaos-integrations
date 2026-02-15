# Excel/CSV → LLM処理統合スクリプト
# 使用方法: python excel_llm_processor.py <ファイルパス> [オプション]

import sys
import json
import pandas as pd
import requests
from pathlib import Path
from typing import Dict, Any, Optional

class ExcelLLMProcessor:
    """Excel/CSVファイルをLLMに渡して処理するクラス"""
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.2:3b"):
        self.ollama_url = ollama_url
        self.model = model
    
    def load_file(self, file_path: str) -> pd.DataFrame:
        """ファイルを読み込む"""
        path = Path(file_path)
        
        if path.suffix.lower() == '.xlsx':
            return pd.read_excel(file_path)
        elif path.suffix.lower() == '.csv':
            return pd.read_csv(file_path)
        else:
            raise ValueError(f"サポートされていないファイル形式: {path.suffix}")
    
    def get_summary(self, df: pd.DataFrame) -> str:
        """データフレームの要約を取得"""
        summary = f"""
データ概要:
- 行数: {len(df)}
- 列数: {len(df.columns)}
- 列名: {', '.join(df.columns.tolist())}
- 欠損値: {df.isnull().sum().sum()}個
"""
        
        # 数値列の統計
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary += f"""
数値列の統計:
{df[numeric_cols].describe().to_string()}
"""
        
        return summary
    
    def process_with_llm(self, df: pd.DataFrame, task: str = "異常値検出") -> Dict[str, Any]:
        """LLMにデータを渡して処理"""
        # データの要約を取得
        summary = self.get_summary(df)
        
        # サンプルデータ（最初の10行）
        sample_data = df.head(10).to_string()
        
        # LLMに送るプロンプト
        prompt = f"""以下のデータを分析してください。

{summary}

サンプルデータ（最初の10行）:
{sample_data}

タスク: {task}

以下の観点で分析してください:
1. 異常値や外れ値の検出
2. データの傾向やパターン
3. 潜在的な問題やミス
4. 改善提案

結果をJSON形式で返してください:
{{
    "anomalies": ["異常値1", "異常値2"],
    "patterns": ["パターン1", "パターン2"],
    "issues": ["問題1", "問題2"],
    "recommendations": ["提案1", "提案2"]
}}
"""
        
        # Ollama APIにリクエスト
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "response": result.get("response", ""),
                "model": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_to_csv(self, df: pd.DataFrame, output_path: str):
        """データフレームをCSVにエクスポート"""
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"CSVファイルを保存しました: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python excel_llm_processor.py <ファイルパス> [タスク]")
        print("例: python excel_llm_processor.py data.xlsx 異常値検出")
        sys.exit(1)
    
    file_path = sys.argv[1]
    task = sys.argv[2] if len(sys.argv) > 2 else "異常値検出"
    
    processor = ExcelLLMProcessor()
    
    print(f"ファイルを読み込み中: {file_path}")
    df = processor.load_file(file_path)
    print(f"  [OK] {len(df)}行 × {len(df.columns)}列のデータを読み込みました")
    
    print(f"\nLLMで処理中: {task}")
    result = processor.process_with_llm(df, task)
    
    if result["success"]:
        print("\n=== LLM分析結果 ===")
        print(result["response"])
        
        # 結果をファイルに保存
        output_path = Path(file_path).stem + "_llm_analysis.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result["response"])
        print(f"\n結果を保存しました: {output_path}")
    else:
        print(f"\n[ERROR] LLM処理に失敗しました: {result['error']}")


if __name__ == "__main__":
    main()
