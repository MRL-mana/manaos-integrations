#!/usr/bin/env python3
"""
🎨 画像バッチ処理エンジン
リサイズ、圧縮、変換を並列実行
"""

import concurrent.futures
from pathlib import Path
from PIL import Image
import time
from datetime import datetime
import json

class ImageBatchProcessor:
    def __init__(self, max_workers=8):
        self.max_workers = max_workers
        self.results = []
        self.stats = {"processed": 0, "failed": 0, "total_time": 0}
    
    def resize_image(self, input_path, output_path, width=None, height=None, quality=85):
        """画像リサイズ"""
        try:
            start = time.time()
            
            with Image.open(input_path) as img:
                # アスペクト比維持リサイズ
                if width and height:
                    img.thumbnail((width, height), Image.Resampling.LANCZOS)
                elif width:
                    ratio = width / img.width
                    height = int(img.height * ratio)
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                elif height:
                    ratio = height / img.height
                    width = int(img.width * ratio)
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                
                # 保存
                img.save(output_path, quality=quality, optimize=True)
            
            elapsed = time.time() - start
            orig_size = Path(input_path).stat().st_size
            new_size = Path(output_path).stat().st_size
            ratio = (1 - new_size / orig_size) * 100
            
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "original_size": orig_size,
                "new_size": new_size,
                "reduction": f"{ratio:.1f}%",
                "time": elapsed
            }
        except Exception as e:
            return {
                "success": False,
                "input": input_path,
                "error": str(e)
            }
    
    def compress_image(self, input_path, output_path, quality=75):
        """画像圧縮"""
        try:
            start = time.time()
            
            with Image.open(input_path) as img:
                # RGBに変換（JPEG用）
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            elapsed = time.time() - start
            orig_size = Path(input_path).stat().st_size
            new_size = Path(output_path).stat().st_size
            ratio = (1 - new_size / orig_size) * 100
            
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "original_size": orig_size,
                "new_size": new_size,
                "reduction": f"{ratio:.1f}%",
                "time": elapsed
            }
        except Exception as e:
            return {
                "success": False,
                "input": input_path,
                "error": str(e)
            }
    
    def convert_format(self, input_path, output_path, target_format='PNG'):
        """画像フォーマット変換"""
        try:
            start = time.time()
            
            with Image.open(input_path) as img:
                # RGBに変換
                if img.mode in ('RGBA', 'LA') and target_format == 'JPEG':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = bg
                
                img.save(output_path, target_format)
            
            elapsed = time.time() - start
            
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "format": target_format,
                "time": elapsed
            }
        except Exception as e:
            return {
                "success": False,
                "input": input_path,
                "error": str(e)
            }
    
    def batch_resize(self, input_dir, output_dir, width=800, height=None, pattern="*"):
        """バッチリサイズ"""
        print(f"🎨 バッチリサイズ: {input_dir} → {output_dir}")
        print(f"   サイズ: {width}x{height if height else 'auto'}")
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 画像ファイル取得
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp']:
            image_files.extend(input_path.glob(ext))
        
        if not image_files:
            print("❌ 画像ファイルが見つかりません")
            return
        
        print(f"   対象: {len(image_files)}ファイル")
        
        # 並列処理
        tasks = []
        for img_file in image_files:
            output_file = output_path / img_file.name
            tasks.append((self.resize_image, (str(img_file), str(output_file), width, height), {}))
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args, **kwargs) for func, args, kwargs in tasks]
            
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                self.results.append(result)
                
                if result['success']:
                    self.stats['processed'] += 1
                    print(f"✅ [{i}/{len(tasks)}] {Path(result['input']).name} ({result['reduction']} 削減)")
                else:
                    self.stats['failed'] += 1
                    print(f"❌ [{i}/{len(tasks)}] {Path(result['input']).name}: {result['error']}")
        
        elapsed = time.time() - start
        self.stats['total_time'] = elapsed
        
        print(f"\n⏱️ 完了: {elapsed:.2f}秒")
        print(f"✅ 成功: {self.stats['processed']}")
        print(f"❌ 失敗: {self.stats['failed']}")
        
        # レポート保存
        self.save_report('resize')
    
    def batch_compress(self, input_dir, output_dir, quality=75):
        """バッチ圧縮"""
        print(f"🎨 バッチ圧縮: {input_dir} → {output_dir}")
        print(f"   品質: {quality}%")
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 画像ファイル取得
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            image_files.extend(input_path.glob(ext))
        
        if not image_files:
            print("❌ 画像ファイルが見つかりません")
            return
        
        print(f"   対象: {len(image_files)}ファイル")
        
        # 並列処理
        tasks = []
        for img_file in image_files:
            output_file = output_path / f"{img_file.stem}.jpg"
            tasks.append((self.compress_image, (str(img_file), str(output_file), quality), {}))
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args, **kwargs) for func, args, kwargs in tasks]
            
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                self.results.append(result)
                
                if result['success']:
                    self.stats['processed'] += 1
                    print(f"✅ [{i}/{len(tasks)}] {Path(result['input']).name} ({result['reduction']} 削減)")
                else:
                    self.stats['failed'] += 1
                    print(f"❌ [{i}/{len(tasks)}] {Path(result['input']).name}: {result['error']}")
        
        elapsed = time.time() - start
        self.stats['total_time'] = elapsed
        
        print(f"\n⏱️ 完了: {elapsed:.2f}秒")
        print(f"✅ 成功: {self.stats['processed']}")
        print(f"❌ 失敗: {self.stats['failed']}")
        
        # レポート保存
        self.save_report('compress')
    
    def save_report(self, operation_type):
        """レポート保存"""
        report_file = f"/root/logs/image_batch_{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump({
                "operation": operation_type,
                "timestamp": datetime.now().isoformat(),
                "stats": self.stats,
                "results": self.results
            }, f, indent=2)
        
        print(f"📄 レポート: {report_file}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("使い方:")
        print("  python3 image_batch_processor.py resize <input_dir> <output_dir> [width] [height]")
        print("  python3 image_batch_processor.py compress <input_dir> <output_dir> [quality]")
        sys.exit(1)
    
    processor = ImageBatchProcessor(max_workers=8)
    
    operation = sys.argv[1]
    input_dir = sys.argv[2]
    output_dir = sys.argv[3]
    
    if operation == 'resize':
        width = int(sys.argv[4]) if len(sys.argv) > 4 else 800
        height = int(sys.argv[5]) if len(sys.argv) > 5 else None
        processor.batch_resize(input_dir, output_dir, width, height)
    elif operation == 'compress':
        quality = int(sys.argv[4]) if len(sys.argv) > 4 else 75
        processor.batch_compress(input_dir, output_dir, quality)
    else:
        print(f"❌ 不明な操作: {operation}")

