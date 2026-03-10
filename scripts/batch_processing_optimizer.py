#!/usr/bin/env python3
"""
バッチ処理最適化システム
大量ファイル処理、メモリ使用量監視、並列処理最適化
"""

import asyncio
import json
import logging
import os
import sys
import time
import psutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 既存システムのインポート
sys.path.append('/root')
from enhanced_pdf_excel_system import EnhancedPDFExcelSystem
from pdf_excel_converter import PDFExcelConverter

class BatchProcessingOptimizer:
    """バッチ処理最適化システム"""
    
    def __init__(self):
        self.logger = logging.getLogger("BatchProcessingOptimizer")
        self.logger.setLevel(logging.INFO)
        
        # システム初期化
        self.enhanced_system = EnhancedPDFExcelSystem()
        self.pdf_converter = PDFExcelConverter()
        
        # バッチ処理設定
        self.batch_config = {
            "system_name": "バッチ処理最適化システム",
            "version": "1.0.0",
            "test_directory": "/root/batch_processing_tests",
            "output_directory": "/root/excel_output",
            "temp_directory": "/tmp/pdf_excel_converter",
            "max_concurrent_tasks": 5,
            "memory_limit_mb": 2048,  # 2GB
            "cpu_limit_percent": 80,  # 80%
            "timeout_seconds": 300,   # 5分
            "batch_sizes": [1, 3, 5, 10, 20],  # テスト用バッチサイズ
            "monitoring_interval": 1  # 1秒間隔でモニタリング
        }
        
        # テストディレクトリ作成
        Path(self.batch_config["test_directory"]).mkdir(parents=True, exist_ok=True)
        
        # システムリソース監視
        self.system_monitor = SystemResourceMonitor()
        
        self.logger.info("🚀 バッチ処理最適化システム初期化完了")
    
    def create_batch_test_pdfs(self, count: int) -> List[str]:
        """バッチテスト用PDFファイル作成"""
        try:
            self.logger.info(f"📄 バッチテスト用PDF作成開始: {count}ファイル")
            
            pdf_files = []
            for i in range(count):
                pdf_path = self.create_single_test_pdf(i + 1)
                if pdf_path:
                    pdf_files.append(pdf_path)
            
            self.logger.info(f"✅ バッチテスト用PDF作成完了: {len(pdf_files)}ファイル")
            return pdf_files
            
        except Exception as e:
            self.logger.error(f"❌ バッチテスト用PDF作成エラー: {e}")
            return []
    
    def create_single_test_pdf(self, index: int) -> str:
        """単一テストPDF作成"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            
            pdf_path = os.path.join(self.batch_config["test_directory"], f"batch_test_{index:03d}.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # ヘッダー
            header = Paragraph(f"バッチテストファイル {index} - バッチ処理最適化システム", styles['Title'])
            story.append(header)
            story.append(Spacer(1, 20))
            
            # テストデータ表
            test_table_data = [
                ['項目', '値', '単位', '備考'],
                ['ファイル番号', str(index), '番', f'テストファイル{index}'],
                ['作成日時', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '日時', '自動生成'],
                ['処理時間', '0.1', '秒', '予想処理時間'],
                ['ファイルサイズ', '1.5', 'KB', '予想ファイルサイズ'],
                ['表データ数', '5', '行', 'テストデータ'],
                ['テキスト長', '200', '文字', 'テストテキスト'],
                ['OCR対象', 'なし', '', '画像なし']
            ]
            
            test_table = Table(test_table_data)
            test_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            
            story.append(test_table)
            
            doc.build(story)
            
            return pdf_path
            
        except Exception as e:
            self.logger.error(f"❌ 単一テストPDF作成エラー ({index}): {e}")
            return None  # type: ignore
    
    async def test_sequential_processing(self, pdf_files: List[str]) -> Dict[str, Any]:
        """逐次処理テスト"""
        try:
            self.logger.info(f"🔄 逐次処理テスト開始: {len(pdf_files)}ファイル")
            
            start_time = time.time()
            results = []
            
            for i, pdf_path in enumerate(pdf_files):
                # システムリソース監視開始
                monitor_start = time.time()
                self.system_monitor.start_monitoring()
                
                # 変換実行
                result = await self.pdf_converter.convert_pdf_to_excel(
                    pdf_path=pdf_path,
                    config={
                        "table_detection": True,
                        "ocr_enabled": False,
                        "language": "jpn"
                    }
                )
                
                # システムリソース監視終了
                monitor_end = time.time()
                self.system_monitor.stop_monitoring()
                
                if result.get("success"):
                    results.append({
                        "file_index": i + 1,
                        "pdf_file": os.path.basename(pdf_path),
                        "success": True,
                        "processing_time": result.get("processing_time", 0),
                        "tables_extracted": result.get("extraction_summary", {}).get("tables_extracted", 0),
                        "memory_usage": self.system_monitor.get_max_memory_usage(),
                        "cpu_usage": self.system_monitor.get_max_cpu_usage()
                    })
                else:
                    results.append({
                        "file_index": i + 1,
                        "pdf_file": os.path.basename(pdf_path),
                        "success": False,
                        "error": result.get("error", "不明なエラー")
                    })
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.logger.info(f"✅ 逐次処理テスト完了: {total_time:.2f}秒")
            
            return {
                "processing_type": "sequential",
                "total_files": len(pdf_files),
                "successful_files": sum(1 for r in results if r.get("success", False)),
                "failed_files": sum(1 for r in results if not r.get("success", False)),
                "total_processing_time": total_time,
                "average_processing_time": total_time / len(pdf_files) if pdf_files else 0,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 逐次処理テストエラー: {e}")
            return {
                "processing_type": "sequential",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_parallel_processing(self, pdf_files: List[str], max_workers: int = 5) -> Dict[str, Any]:
        """並列処理テスト"""
        try:
            self.logger.info(f"🔄 並列処理テスト開始: {len(pdf_files)}ファイル (並列度: {max_workers})")
            
            start_time = time.time()
            results = []
            
            # セマフォで同時実行数を制限
            semaphore = asyncio.Semaphore(max_workers)
            
            async def process_single_file(pdf_path: str, index: int):
                async with semaphore:
                    # システムリソース監視開始
                    self.system_monitor.start_monitoring()
                    
                    # 変換実行
                    result = await self.pdf_converter.convert_pdf_to_excel(
                        pdf_path=pdf_path,
                        config={
                            "table_detection": True,
                            "ocr_enabled": False,
                            "language": "jpn"
                        }
                    )
                    
                    # システムリソース監視終了
                    self.system_monitor.stop_monitoring()
                    
                    if result.get("success"):
                        return {
                            "file_index": index + 1,
                            "pdf_file": os.path.basename(pdf_path),
                            "success": True,
                            "processing_time": result.get("processing_time", 0),
                            "tables_extracted": result.get("extraction_summary", {}).get("tables_extracted", 0),
                            "memory_usage": self.system_monitor.get_max_memory_usage(),
                            "cpu_usage": self.system_monitor.get_max_cpu_usage()
                        }
                    else:
                        return {
                            "file_index": index + 1,
                            "pdf_file": os.path.basename(pdf_path),
                            "success": False,
                            "error": result.get("error", "不明なエラー")
                        }
            
            # 並列処理実行
            tasks = [process_single_file(pdf_path, i) for i, pdf_path in enumerate(pdf_files)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 例外処理
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "file_index": i + 1,
                        "pdf_file": os.path.basename(pdf_files[i]),
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.logger.info(f"✅ 並列処理テスト完了: {total_time:.2f}秒")
            
            return {
                "processing_type": "parallel",
                "max_workers": max_workers,
                "total_files": len(pdf_files),
                "successful_files": sum(1 for r in processed_results if r.get("success", False)),
                "failed_files": sum(1 for r in processed_results if not r.get("success", False)),
                "total_processing_time": total_time,
                "average_processing_time": total_time / len(pdf_files) if pdf_files else 0,
                "results": processed_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 並列処理テストエラー: {e}")
            return {
                "processing_type": "parallel",
                "max_workers": max_workers,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_batch_processing(self, batch_size: int) -> Dict[str, Any]:
        """バッチ処理テスト"""
        try:
            self.logger.info(f"📦 バッチ処理テスト開始: バッチサイズ {batch_size}")
            
            # テスト用PDF作成
            pdf_files = self.create_batch_test_pdfs(batch_size)
            if not pdf_files:
                return {
                    "batch_size": batch_size,
                    "success": False,
                    "error": "テスト用PDF作成失敗",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 逐次処理テスト
            sequential_result = await self.test_sequential_processing(pdf_files)
            
            # 並列処理テスト（複数の並列度でテスト）
            parallel_results = []
            for max_workers in [2, 3, 5]:
                parallel_result = await self.test_parallel_processing(pdf_files, max_workers)
                parallel_results.append(parallel_result)
            
            # 結果分析
            analysis = {
                "batch_size": batch_size,
                "total_files": len(pdf_files),
                "sequential_processing": sequential_result,
                "parallel_processing": parallel_results,
                "performance_comparison": self.analyze_performance(sequential_result, parallel_results),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ バッチ処理テスト完了: バッチサイズ {batch_size}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ バッチ処理テストエラー (バッチサイズ {batch_size}): {e}")
            return {
                "batch_size": batch_size,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_performance(self, sequential_result: Dict, parallel_results: List[Dict]) -> Dict[str, Any]:
        """パフォーマンス分析"""
        try:
            analysis = {
                "sequential_time": sequential_result.get("total_processing_time", 0),
                "parallel_times": [pr.get("total_processing_time", 0) for pr in parallel_results],
                "speedup_ratios": [],
                "best_parallel_config": None,
                "recommendations": []
            }
            
            # 高速化比の計算
            for pr in parallel_results:
                parallel_time = pr.get("total_processing_time", 0)
                if parallel_time > 0:
                    speedup = sequential_result.get("total_processing_time", 0) / parallel_time
                    analysis["speedup_ratios"].append({
                        "max_workers": pr.get("max_workers", 0),
                        "speedup": speedup,
                        "parallel_time": parallel_time
                    })
            
            # 最適な並列設定の特定
            if analysis["speedup_ratios"]:
                best_config = max(analysis["speedup_ratios"], key=lambda x: x["speedup"])
                analysis["best_parallel_config"] = best_config
            
            # 推奨事項の生成
            if analysis["best_parallel_config"]:
                best_speedup = analysis["best_parallel_config"]["speedup"]
                if best_speedup > 1.5:
                    analysis["recommendations"].append(f"並列処理を推奨 (高速化比: {best_speedup:.2f}x)")
                elif best_speedup > 1.1:
                    analysis["recommendations"].append(f"並列処理を検討 (高速化比: {best_speedup:.2f}x)")
                else:
                    analysis["recommendations"].append("逐次処理を推奨 (並列処理の効果が限定的)")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ パフォーマンス分析エラー: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_comprehensive_batch_tests(self) -> Dict[str, Any]:
        """包括的なバッチ処理テスト実行"""
        try:
            self.logger.info("🧪 包括的なバッチ処理テスト実行開始")
            
            test_results = {
                "test_suite": "バッチ処理最適化システム",
                "version": self.batch_config["version"],
                "start_time": datetime.now().isoformat(),
                "batch_tests": []
            }
            
            # 各バッチサイズでテスト実行
            for batch_size in self.batch_config["batch_sizes"]:
                batch_result = await self.test_batch_processing(batch_size)
                test_results["batch_tests"].append(batch_result)
            
            test_results["end_time"] = datetime.now().isoformat()
            test_results["total_tests"] = len(test_results["batch_tests"])
            
            # 結果保存
            self.save_test_results(test_results)
            
            self.logger.info(f"✅ 包括的なバッチ処理テスト完了: {test_results['total_tests']}テスト")
            return test_results
            
        except Exception as e:
            self.logger.error(f"❌ 包括的なバッチ処理テストエラー: {e}")
            return {
                "test_suite": "バッチ処理最適化システム",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def save_test_results(self, results: Dict[str, Any]):
        """テスト結果の保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = os.path.join(self.batch_config["test_directory"], f"batch_processing_results_{timestamp}.json")
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ テスト結果保存完了: {results_file}")
            
        except Exception as e:
            self.logger.error(f"❌ テスト結果保存エラー: {e}")

class SystemResourceMonitor:
    """システムリソース監視クラス"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.memory_usage = []
        self.cpu_usage = []
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        """監視開始"""
        self.monitoring = True
        self.memory_usage = []
        self.cpu_usage = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """監視ループ"""
        while self.monitoring:
            try:
                # メモリ使用量取得
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent()
                
                with self.lock:
                    self.memory_usage.append(memory_percent)
                    self.cpu_usage.append(cpu_percent)
                
                time.sleep(0.1)  # 100ms間隔
                
            except Exception:
                break
    
    def get_max_memory_usage(self) -> float:
        """最大メモリ使用量取得"""
        with self.lock:
            return max(self.memory_usage) if self.memory_usage else 0
    
    def get_max_cpu_usage(self) -> float:
        """最大CPU使用量取得"""
        with self.lock:
            return max(self.cpu_usage) if self.cpu_usage else 0

async def main():
    """メイン実行関数"""
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('batch_processing_optimizer.log'),
            logging.StreamHandler()
        ]
    )
    
    optimizer = BatchProcessingOptimizer()
    
    # 包括的なバッチ処理テスト実行
    results = await optimizer.run_comprehensive_batch_tests()
    
    print("🚀 バッチ処理最適化システム 実行完了")
    print("=" * 60)
    
    # 結果サマリー表示
    print("📊 テスト結果サマリー:")
    print(f"   総テスト数: {results.get('total_tests', 0)}")
    print(f"   開始時刻: {results.get('start_time', 'N/A')}")
    print(f"   終了時刻: {results.get('end_time', 'N/A')}")
    
    # 各バッチテストの結果表示
    for i, batch_test in enumerate(results.get('batch_tests', []), 1):
        batch_size = batch_test.get('batch_size', 0)
        print(f"\n📦 バッチサイズ {batch_size}:")
        
        if batch_test.get('success', True):
            sequential = batch_test.get('sequential_processing', {})
            parallel = batch_test.get('parallel_processing', [])
            performance = batch_test.get('performance_comparison', {})
            
            print(f"   逐次処理時間: {sequential.get('total_processing_time', 0):.2f}秒")
            
            for pr in parallel:
                max_workers = pr.get('max_workers', 0)
                parallel_time = pr.get('total_processing_time', 0)
                print(f"   並列処理時間 ({max_workers}並列): {parallel_time:.2f}秒")
            
            if performance.get('best_parallel_config'):
                best_config = performance['best_parallel_config']
                print(f"   最適設定: {best_config['max_workers']}並列 (高速化比: {best_config['speedup']:.2f}x)")
        else:
            print(f"   ❌ テスト失敗: {batch_test.get('error', '不明なエラー')}")

if __name__ == "__main__":
    asyncio.run(main())



