#!/usr/bin/env python3
"""
日報PDF→Excel変換スクリプト
Mana専用・超簡単仕様

使い方:
  python3 nippo_to_excel.py [PDFファイル]
  python3 nippo_to_excel.py [フォルダ]
  python3 nippo_to_excel.py  # 対話モード
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# 既存の超強化版システムをインポート
sys.path.insert(0, '/root/organized_workspace/utilities')
from mana_pdf_excel_advanced import ManaPDFExcelAdvanced

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/nippo_to_excel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NippoToExcel")


class NippoToExcel:
    """日報PDF→Excel変換システム"""
    
    def __init__(self):
        self.converter = ManaPDFExcelAdvanced()
        self.output_dir = Path('/root/daily_reports/excel')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 出力先を日報専用フォルダに変更
        self.converter.output_dir = self.output_dir
        
    def convert_single_pdf(self, pdf_path: str, use_ocr: bool = False) -> dict:
        """単一PDF変換"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return {'success': False, 'error': f'ファイルが見つかりません: {pdf_path}'}
        
        if pdf_path.suffix.lower() != '.pdf':
            return {'success': False, 'error': 'PDFファイルではありません'}
        
        print(f"\n📄 変換中: {pdf_path.name}")
        print(f"   出力先: {self.output_dir}")
        
        # カスタム名（日報の日付を含める）
        custom_name = f"日報_{pdf_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = self.converter.convert_pdf_to_excel(
            pdf_path=str(pdf_path),
            use_ocr=use_ocr,
            custom_name=custom_name
        )
        
        if result['success']:
            print("\n✅ 変換完了！")
            print(f"   📊 Excelファイル: {result.get('excel_file', 'N/A')}")
            print(f"   📈 抽出表数: {result.get('total_tables', 0)}")
            print(f"   ⭐ 高品質表数: {result.get('high_quality_tables', 0)}")
            if 'total_text_chars' in result:
                print(f"   📏 抽出文字数: {result['total_text_chars']}")
        else:
            print(f"\n❌ 変換失敗: {result.get('error', '不明なエラー')}")
        
        return result
    
    def convert_folder(self, folder_path: str, use_ocr: bool = False) -> dict:
        """フォルダ内の全PDF一括変換"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            return {'success': False, 'error': 'フォルダが見つかりません'}
        
        # PDFファイルを検索
        pdf_files = list(folder_path.glob('*.pdf'))
        pdf_files.extend(list(folder_path.glob('*.PDF')))
        
        if not pdf_files:
            return {'success': False, 'error': 'PDFファイルが見つかりません'}
        
        print(f"\n📁 フォルダ内のPDF: {len(pdf_files)}個")
        print(f"   出力先: {self.output_dir}\n")
        
        # バッチ変換
        results = {
            'total': len(pdf_files),
            'success': 0,
            'failed': 0,
            'files': []
        }
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] ", end='')
            result = self.convert_single_pdf(pdf_file, use_ocr=use_ocr)
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['files'].append({
                'pdf': str(pdf_file),
                'result': result
            })
        
        # サマリー表示
        print(f"\n{'='*60}")
        print("📊 一括変換完了サマリー")
        print(f"{'='*60}")
        print(f"   総ファイル数: {results['total']}")
        print(f"   ✅ 成功: {results['success']}")
        print(f"   ❌ 失敗: {results['failed']}")
        print(f"   📁 出力先: {self.output_dir}")
        print(f"{'='*60}\n")
        
        return results
    
    def interactive_mode(self):
        """対話モード"""
        print("\n" + "="*60)
        print("📊 日報PDF→Excel変換システム")
        print("="*60)
        
        print("\n変換したいPDFファイルまたはフォルダのパスを入力してください:")
        print("（何も入力せずEnterで /root/daily_reports を検索）")
        
        user_input = input("\n> ").strip()
        
        if not user_input:
            # デフォルトは /root/daily_reports
            target_path = Path('/root/daily_reports')
        else:
            target_path = Path(user_input)
        
        # OCR使用確認
        print("\nOCRを使用しますか？（画像化されたPDFの場合に必要）")
        print("  y: はい（処理時間が増加）")
        print("  n: いいえ（通常のPDF）")
        
        use_ocr_input = input("\n> ").strip().lower()
        use_ocr = use_ocr_input in ['y', 'yes', 'はい']
        
        # 変換実行
        if target_path.is_file():
            self.convert_single_pdf(target_path, use_ocr=use_ocr)
        elif target_path.is_dir():
            self.convert_folder(target_path, use_ocr=use_ocr)
        else:
            print(f"\n❌ パスが見つかりません: {target_path}")


def main():
    """メイン処理"""
    nippo = NippoToExcel()
    
    if len(sys.argv) == 1:
        # 引数なし = 対話モード
        nippo.interactive_mode()
    
    elif len(sys.argv) >= 2:
        # 引数あり = ファイルまたはフォルダパス
        target = sys.argv[1]
        
        # OCRフラグチェック
        use_ocr = '--ocr' in sys.argv or '-o' in sys.argv
        
        target_path = Path(target)
        
        if target_path.is_file():
            nippo.convert_single_pdf(target, use_ocr=use_ocr)
        elif target_path.is_dir():
            nippo.convert_folder(target, use_ocr=use_ocr)
        else:
            print(f"❌ パスが見つかりません: {target}")
            print("\n使い方:")
            print("  python3 nippo_to_excel.py [PDFファイル]")
            print("  python3 nippo_to_excel.py [フォルダ]")
            print("  python3 nippo_to_excel.py [ファイル] --ocr  # OCR使用")
            print("  python3 nippo_to_excel.py  # 対話モード")
            sys.exit(1)
    
    else:
        # ヘルプ表示
        print("使い方:")
        print("  python3 nippo_to_excel.py [PDFファイル]")
        print("  python3 nippo_to_excel.py [フォルダ]")
        print("  python3 nippo_to_excel.py [ファイル] --ocr  # OCR使用")
        print("  python3 nippo_to_excel.py  # 対話モード")


if __name__ == '__main__':
    main()

