#!/usr/bin/env python3
"""
📊 Data Processor - データ処理エンジン
CSV、JSON、Excel並列処理
"""

import concurrent.futures
import csv
import json
import pandas as pd
from pathlib import Path
import time

class DataProcessor:
    def __init__(self, max_workers=8):
        self.max_workers = max_workers
        self.results = []
    
    def csv_to_json(self, csv_file, json_file):
        """CSV→JSON変換"""
        try:
            start = time.time()
            
            data = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "input": csv_file,
                "output": json_file,
                "rows": len(data),
                "time": time.time() - start
            }
        except Exception as e:
            return {"success": False, "input": csv_file, "error": str(e)}
    
    def json_to_csv(self, json_file, csv_file):
        """JSON→CSV変換"""
        try:
            start = time.time()
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            if data:
                keys = data[0].keys()
                with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(data)
            
            return {
                "success": True,
                "input": json_file,
                "output": csv_file,
                "rows": len(data),
                "time": time.time() - start
            }
        except Exception as e:
            return {"success": False, "input": json_file, "error": str(e)}
    
    def csv_filter(self, input_file, output_file, column, value):
        """CSVフィルタリング"""
        try:
            start = time.time()
            
            df = pd.read_csv(input_file)
            filtered = df[df[column] == value]
            filtered.to_csv(output_file, index=False)
            
            return {
                "success": True,
                "input": input_file,
                "output": output_file,
                "original_rows": len(df),
                "filtered_rows": len(filtered),
                "time": time.time() - start
            }
        except Exception as e:
            return {"success": False, "input": input_file, "error": str(e)}
    
    def batch_convert(self, input_dir, output_dir, from_format, to_format):
        """バッチ変換"""
        print(f"📊 バッチ変換: {from_format} → {to_format}")
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル検索
        files = list(input_path.glob(f"*.{from_format}"))
        
        if not files:
            print(f"❌ {from_format}ファイルが見つかりません")
            return
        
        print(f"   対象: {len(files)}ファイル")
        
        # 変換関数選択
        if from_format == "csv" and to_format == "json":
            convert_func = self.csv_to_json
        elif from_format == "json" and to_format == "csv":
            convert_func = self.json_to_csv
        else:
            print(f"❌ 未対応: {from_format} → {to_format}")
            return
        
        # タスク準備
        tasks = []
        for f in files:
            output_file = output_path / f"{f.stem}.{to_format}"
            tasks.append((convert_func, (str(f), str(output_file)), {}))
        
        # 並列実行
        start = time.time()
        success = 0
        failed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args, **kwargs) for func, args, kwargs in tasks]
            
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                
                if result["success"]:
                    success += 1
                    print(f"✅ [{i}/{len(tasks)}] {Path(result['input']).name} ({result.get('rows', 0)}行)")
                else:
                    failed += 1
                    print(f"❌ [{i}/{len(tasks)}] {Path(result['input']).name}: {result['error']}")
        
        elapsed = time.time() - start
        
        print(f"\n⏱️ 完了: {elapsed:.2f}秒")
        print(f"✅ 成功: {success}")
        print(f"❌ 失敗: {failed}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("使い方:")
        print("  python3 data_processor.py <input_dir> <output_dir> <from_format> <to_format>")
        print("")
        print("例:")
        print("  python3 data_processor.py /data/csv /data/json csv json")
        print("  python3 data_processor.py /data/json /data/csv json csv")
        sys.exit(1)
    
    processor = DataProcessor(max_workers=8)
    processor.batch_convert(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

