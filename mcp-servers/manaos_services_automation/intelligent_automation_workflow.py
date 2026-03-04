#!/usr/bin/env python3
"""
インテリジェント自動化ワークフロー
完全自動化されたPDF-Excel変換システム
"""

import asyncio
import time
import logging
from typing import List, Dict, Any
from pathlib import Path
import json
import shutil
from datetime import datetime, timedelta
import os
import glob

# 既存システムのインポート
from final_production_converter import FinalProductionConverter
from advanced_ocr_enhancer import AdvancedOCREnhancer
from intelligent_table_recognizer import IntelligentTableRecognizer
from advanced_system_optimizer import SystemOptimizer

class IntelligentAutomationWorkflow:
    def __init__(self):
        self.setup_logging()
        self.pdf_converter = FinalProductionConverter()
        self.ocr_enhancer = AdvancedOCREnhancer()
        self.table_recognizer = IntelligentTableRecognizer()
        self.optimizer = SystemOptimizer()
        
        # ワークフロー設定
        self.config = {
            'watch_directories': [
                '/tmp/automation_input',
                '/home/mana/Desktop/automation_input',
                '/root/automation_input'
            ],
            'output_directory': '/tmp/automation_output',
            'processed_directory': '/tmp/automation_processed',
            'error_directory': '/tmp/automation_error',
            'batch_size': 5,
            'max_workers': 3,
            'auto_cleanup_days': 7,
            'notification_webhook': None,
            'quality_threshold': 70.0
        }
        
        # ディレクトリ作成
        self._setup_directories()
        
        # ワークフロー状態
        self.workflow_stats = {
            'total_processed': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'last_cleanup': None,
            'current_batch': None,
            'workflow_started': datetime.now()
        }
        
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/tmp/automation_workflow.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AutomationWorkflow')
        
    def _setup_directories(self):
        """必要なディレクトリを作成"""
        for directory in [
            self.config['output_directory'],
            self.config['processed_directory'],
            self.config['error_directory']
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
        # 監視ディレクトリも作成
        for watch_dir in self.config['watch_directories']:
            Path(watch_dir).mkdir(parents=True, exist_ok=True)
            
        self.logger.info("📁 ワークフロー用ディレクトリ設定完了")
        
    async def scan_input_directories(self) -> List[str]:
        """入力ディレクトリをスキャンしてPDFファイルを検索"""
        pdf_files = []
        
        for watch_dir in self.config['watch_directories']:
            if os.path.exists(watch_dir):
                pattern = os.path.join(watch_dir, "*.pdf")
                found_files = glob.glob(pattern)
                pdf_files.extend(found_files)
                
        self.logger.info(f"🔍 スキャン結果: {len(pdf_files)}個のPDFファイルを発見")
        return pdf_files
        
    async def process_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """単一PDFファイルの処理"""
        start_time = time.time()
        filename = os.path.basename(pdf_path)
        
        try:
            self.logger.info(f"🔄 処理開始: {filename}")
            
            # ファイルを一時ディレクトリにコピー
            temp_path = f"/tmp/automation_temp_{filename}"
            shutil.copy2(pdf_path, temp_path)
            
            # 変換実行
            output_filename = filename.replace('.pdf', '.xlsx')
            output_path = os.path.join(self.config['output_directory'], output_filename)
            
            # 高品質変換実行
            result = await self._enhanced_conversion(temp_path, output_path)
            
            # 品質チェック
            quality_score = self._calculate_quality_score(result)
            
            if quality_score >= self.config['quality_threshold']:
                # 成功処理
                processed_path = os.path.join(self.config['processed_directory'], filename)
                shutil.move(pdf_path, processed_path)
                
                self.workflow_stats['successful_conversions'] += 1
                status = 'success'
                
                self.logger.info(f"✅ 処理成功: {filename} (品質スコア: {quality_score:.1f})")
            else:
                # 品質不足
                error_path = os.path.join(self.config['error_directory'], f"low_quality_{filename}")
                shutil.move(pdf_path, error_path)
                
                self.workflow_stats['failed_conversions'] += 1
                status = 'low_quality'
                
                self.logger.warning(f"⚠️ 品質不足: {filename} (品質スコア: {quality_score:.1f})")
            
            # 一時ファイル削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            processing_time = time.time() - start_time
            
            return {
                'filename': filename,
                'status': status,
                'quality_score': quality_score,
                'processing_time': processing_time,
                'output_file': output_path if status == 'success' else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 処理エラー: {filename} - {e}")
            
            # エラーファイルを移動
            try:
                error_path = os.path.join(self.config['error_directory'], f"error_{filename}")
                shutil.move(pdf_path, error_path)
            except IOError as e:
                pass
                
            self.workflow_stats['failed_conversions'] += 1
            
            return {
                'filename': filename,
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _enhanced_conversion(self, pdf_path: str, output_path: str) -> Dict[str, Any]:
        """高品質変換処理"""
        # OCR強化
        ocr_result = self.ocr_enhancer.enhance_ocr_accuracy(pdf_path)
        
        # 表認識強化
        table_result = self.table_recognizer.hybrid_table_extraction(pdf_path)
        
        # 変換実行
        conversion_result = self.pdf_converter.convert_pdf_to_excel(pdf_path, output_path)
        
        return {
            'ocr_result': ocr_result,
            'table_result': table_result,
            'conversion_result': conversion_result
        }
    
    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """品質スコア計算"""
        score = 0.0
        
        # OCR品質スコア
        if 'ocr_result' in result and result['ocr_result'].get('success'):
            ocr_analysis = result['ocr_result'].get('analysis', {})
            score += ocr_analysis.get('quality_score', 0) * 0.4
            
        # 表認識品質スコア
        if 'table_result' in result and result['table_result'].get('success'):
            table_analysis = result['table_result'].get('best_analysis', {})
            complexity_score = table_analysis.get('complexity_score', 0)
            score += min(complexity_score, 100) * 0.3
            
        # 変換結果品質スコア
        if 'conversion_result' in result:
            conv_result = result['conversion_result']
            if conv_result.get('success'):
                score += 30.0  # ベーススコア
                
                # データ量によるボーナス
                total_rows = conv_result.get('total_data_rows', 0)
                score += min(total_rows / 10, 20)  # 最大20点ボーナス
                
        return min(score, 100.0)
    
    async def process_batch(self, pdf_files: List[str]) -> List[Dict[str, Any]]:
        """バッチ処理"""
        if not pdf_files:
            return []
            
        self.logger.info(f"🔄 バッチ処理開始: {len(pdf_files)}ファイル")
        
        # バッチサイズで分割
        batch_size = self.config['batch_size']
        batches = [pdf_files[i:i+batch_size] for i in range(0, len(pdf_files), batch_size)]
        
        all_results = []
        
        for batch_num, batch in enumerate(batches, 1):
            self.logger.info(f"📦 バッチ {batch_num}/{len(batches)} 処理中")
            
            # 並列処理
            semaphore = asyncio.Semaphore(self.config['max_workers'])
            
            async def process_with_semaphore(pdf_path):
                async with semaphore:
                    return await self.process_single_pdf(pdf_path)
            
            batch_results = await asyncio.gather(
                *[process_with_semaphore(pdf) for pdf in batch],
                return_exceptions=True
            )
            
            # 例外処理
            processed_results = []
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'filename': os.path.basename(batch[i]),
                        'status': 'error',
                        'error': str(result),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    processed_results.append(result)
            
            all_results.extend(processed_results)
            
            # バッチ間でメモリ最適化
            await self.optimizer.optimize_memory_usage()
            
        self.workflow_stats['total_processed'] += len(pdf_files)
        self.logger.info(f"✅ バッチ処理完了: {len(all_results)}ファイル処理")
        
        return all_results
    
    async def cleanup_old_files(self):
        """古いファイルのクリーンアップ"""
        self.logger.info("🧹 古いファイルのクリーンアップ開始")
        
        cutoff_date = datetime.now() - timedelta(days=self.config['auto_cleanup_days'])
        cleaned_count = 0
        
        for directory in [
            self.config['processed_directory'],
            self.config['error_directory'],
            self.config['output_directory']
        ]:
            if os.path.exists(directory):
                for file_path in glob.glob(os.path.join(directory, "*")):
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        self.logger.warning(f"⚠️ クリーンアップエラー: {file_path} - {e}")
        
        self.workflow_stats['last_cleanup'] = datetime.now().isoformat()
        self.logger.info(f"✅ クリーンアップ完了: {cleaned_count}ファイル削除")
        
    def save_workflow_stats(self):
        """ワークフロー統計を保存"""
        stats_path = '/tmp/automation_workflow_stats.json'
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.workflow_stats, f, ensure_ascii=False, indent=2)
    
    async def run_workflow_cycle(self):
        """ワークフローサイクル実行"""
        self.logger.info("🔄 ワークフローサイクル開始")
        
        try:
            # 入力ディレクトリスキャン
            pdf_files = await self.scan_input_directories()
            
            if pdf_files:
                # バッチ処理実行
                results = await self.process_batch(pdf_files)
                
                # 結果統計
                success_count = sum(1 for r in results if r['status'] == 'success')
                error_count = sum(1 for r in results if r['status'] == 'error')
                low_quality_count = sum(1 for r in results if r['status'] == 'low_quality')
                
                self.logger.info(f"📊 サイクル結果: 成功={success_count}, エラー={error_count}, 低品質={low_quality_count}")
            else:
                self.logger.info("📁 処理対象ファイルなし")
            
            # システム最適化
            await self.optimizer.auto_optimize_system()
            
            # 統計保存
            self.save_workflow_stats()
            
        except Exception as e:
            self.logger.error(f"❌ ワークフローサイクルエラー: {e}")
    
    async def start_continuous_workflow(self, interval_minutes: int = 5):
        """連続ワークフロー開始"""
        self.logger.info(f"🚀 連続ワークフロー開始 (間隔: {interval_minutes}分)")
        
        while True:
            try:
                await self.run_workflow_cycle()
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                self.logger.info("⏹️ ワークフロー停止")
                break
            except Exception as e:
                self.logger.error(f"❌ ワークフローエラー: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機

def main():
    """メイン実行関数"""
    print("🚀 インテリジェント自動化ワークフロー開始")
    print("=" * 60)
    
    workflow = IntelligentAutomationWorkflow()
    
    print("📋 **ワークフロー設定:**")
    print(f"• 監視ディレクトリ: {len(workflow.config['watch_directories'])}個")
    print(f"• バッチサイズ: {workflow.config['batch_size']}")
    print(f"• 最大ワーカー数: {workflow.config['max_workers']}")
    print(f"• 品質閾値: {workflow.config['quality_threshold']}")
    print(f"• 自動クリーンアップ: {workflow.config['auto_cleanup_days']}日")
    
    print("\n🎯 **監視ディレクトリ:**")
    for i, watch_dir in enumerate(workflow.config['watch_directories'], 1):
        print(f"{i}. {watch_dir}")
    
    print("\n📁 **出力ディレクトリ:**")
    print(f"• 変換結果: {workflow.config['output_directory']}")
    print(f"• 処理済み: {workflow.config['processed_directory']}")
    print(f"• エラーファイル: {workflow.config['error_directory']}")
    
    print("\n🚀 **自動化ワークフロー開始中...**")
    print("PDFファイルを監視ディレクトリに配置すると自動変換されます")
    
    # 連続ワークフロー開始（5分間隔）
    asyncio.run(workflow.start_continuous_workflow(interval_minutes=5))

if __name__ == "__main__":
    main()

