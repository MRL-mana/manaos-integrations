#!/usr/bin/env python3
"""
ManaOS PDF to Excel Agent
Trinity、Mana、Konohaが使えるPDF→Excel変換エージェント
"""

from typing import Dict, Any, List
import logging
from mana_pdf_excel_advanced import ManaPDFExcelAdvanced
import sys
import os
sys.path.append('/root')

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDFExcelAgent")


class PDFExcelAgent:
    """ManaOS用PDF→Excelエージェント"""

    def __init__(self):
        self.converter = ManaPDFExcelAdvanced()
        self.name = "PDF Excel Converter"
        self.version = "1.0.0"
        self.capabilities = [
            "pdf_to_excel",
            "batch_conversion",
            "table_extraction",
            "data_type_detection",
            "quality_analysis",
            "google_drive_upload"
        ]

        logger.info(f"🚀 {self.name} v{self.version} 初期化完了")

    def get_info(self) -> Dict[str, Any]:
        """エージェント情報を取得"""
        return {
            'name': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'status': 'active',
            'stats': self.converter.stats
        }

    def convert_pdf(self, pdf_path: str, use_ocr: bool = False,
                    upload_to_drive: bool = False) -> Dict[str, Any]:
        """
        PDFをExcelに変換

        Args:
            pdf_path: PDFファイルパス
            use_ocr: OCR使用フラグ
            upload_to_drive: Google Driveアップロードフラグ

        Returns:
            変換結果の辞書
        """
        logger.info(f"📄 PDF変換リクエスト: {os.path.basename(pdf_path)}")

        try:
            # 変換実行
            result = self.converter.convert_pdf_to_excel(
                pdf_path=pdf_path,
                use_ocr=use_ocr
            )

            if result['success'] and upload_to_drive:
                # Google Driveアップロード
                try:
                    sys.path.append('/root/scripts/excel_tools')
                    from upload_excel_to_gdrive import upload_excel_to_gdrive
                    drive_result = upload_excel_to_gdrive(result['excel_path'])
                    if drive_result:
                        result['drive_link'] = drive_result.get('link')
                        result['drive_file_id'] = drive_result.get('id')
                        logger.info(
                            f"✅ Google Driveアップロード成功: {drive_result.get('link')}")
                    else:
                        logger.warning("⚠️ Google Driveアップロード失敗: 結果がNone")
                except Exception as e:
                    logger.warning(f"⚠️ Google Driveアップロード失敗: {e}")

            return result

        except Exception as e:
            logger.error(f"❌ 変換エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def batch_convert(self, pdf_paths: List[str], use_ocr: bool = False) -> Dict[str, Any]:
        """
        複数PDFを一括変換

        Args:
            pdf_paths: PDFファイルパスのリスト
            use_ocr: OCR使用フラグ

        Returns:
            バッチ変換結果
        """
        logger.info(f"📁 バッチ変換リクエスト: {len(pdf_paths)}ファイル")

        try:
            result = self.converter.batch_convert(pdf_paths, use_ocr)
            return result

        except Exception as e:
            logger.error(f"❌ バッチ変換エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return self.converter.get_stats()

    def handle_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        コマンドハンドラー（Trinity、Mana、Konoha用）

        Args:
            command: コマンド名
            params: パラメータ辞書

        Returns:
            実行結果
        """
        logger.info(f"🎯 コマンド受信: {command}")

        if command == "convert_pdf":
            return self.convert_pdf(
                pdf_path=params.get('pdf_path'),
                use_ocr=params.get('use_ocr', False),
                upload_to_drive=params.get('upload_to_drive', False)
            )

        elif command == "batch_convert":
            return self.batch_convert(
                pdf_paths=params.get('pdf_paths', []),
                use_ocr=params.get('use_ocr', False)
            )

        elif command == "get_stats":
            return self.get_stats()

        elif command == "get_info":
            return self.get_info()

        else:
            return {
                'success': False,
                'error': f"Unknown command: {command}"
            }


# グローバルエージェントインスタンス
_agent = None


def get_agent() -> PDFExcelAgent:
    """エージェントインスタンスを取得"""
    global _agent
    if _agent is None:
        _agent = PDFExcelAgent()
    return _agent


# Trinity/Mana/Konoha用のシンプルなAPI
def pdf_to_excel(pdf_path: str, use_ocr: bool = False,
                 upload_to_drive: bool = False) -> Dict[str, Any]:
    """PDFをExcelに変換（Trinity用API）"""
    agent = get_agent()
    return agent.convert_pdf(pdf_path, use_ocr, upload_to_drive)


def batch_pdf_to_excel(pdf_paths: List[str], use_ocr: bool = False) -> Dict[str, Any]:
    """複数PDFを変換（Trinity用API）"""
    agent = get_agent()
    return agent.batch_convert(pdf_paths, use_ocr)


def get_conversion_stats() -> Dict[str, Any]:
    """変換統計を取得（Trinity用API）"""
    agent = get_agent()
    return agent.get_stats()


if __name__ == "__main__":
    # テスト実行
    print("🧪 PDF Excel Agent テスト")
    print("=" * 60)

    agent = get_agent()
    info = agent.get_info()

    print(f"📊 エージェント名: {info['name']}")
    print(f"📦 バージョン: {info['version']}")
    print("⚡ 機能:")
    for cap in info['capabilities']:
        print(f"  • {cap}")

    print("\n✅ ManaOS統合準備完了！")
    print("\nTrinity/Mana/Konohaからの使用例:")
    print("```python")
    print("from manaos_agents.pdf_excel_agent import pdf_to_excel")
    print("")
    print("result = pdf_to_excel('/path/to/file.pdf', upload_to_drive=True)")
    print("if result['success']:")
    print("    print(f\"✅ {result['excel_file']}\")")
    print("    print(f\"☁️ {result.get('drive_link')}\")")
    print("```")
