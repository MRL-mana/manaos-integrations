"""
Excel/CSV → LLM処理統合モジュール
ManaOS統合システム用
"""

import os
import json
import pandas as pd
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from manaos_logger import get_logger, get_service_logger

from _paths import OLLAMA_PORT

logger = get_service_logger("excel-llm-integration")

# excel_llm_processor.pyからExcelLLMProcessorをインポート
try:
    from excel_llm_processor import ExcelLLMProcessor
    EXCEL_LLM_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.warning("excel_llm_processorモジュールが見つかりません")
    EXCEL_LLM_PROCESSOR_AVAILABLE = False
    ExcelLLMProcessor = None


class ExcelLLMIntegration:
    """Excel/CSV → LLM処理統合クラス"""
    
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            ollama_url: Ollama URL（環境変数OLLAMA_URLからも取得可能）
            model: 使用するモデル名（環境変数OLLAMA_MODELからも取得可能）
        """
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.processor = None
        
        if EXCEL_LLM_PROCESSOR_AVAILABLE:
            try:
                self.processor = ExcelLLMProcessor(
                    ollama_url=self.ollama_url,
                    model=self.model
                )
                logger.info(f"ExcelLLMProcessorを初期化しました: {self.ollama_url}, {self.model}")
            except Exception as e:
                logger.warning(f"ExcelLLMProcessorの初期化に失敗: {e}")
    
    def is_available(self) -> bool:
        """
        Excel/LLM処理が利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        if not EXCEL_LLM_PROCESSOR_AVAILABLE:
            return False
        
        if self.processor is None:
            return False
        
        # Ollamaサービスが起動しているか確認
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=3
            )
            if response.status_code == 200:
                return True
        except Exception as e:
            logger.debug(f"Ollamaサービス確認エラー: {e}")
        
        return False
    
    def process_file(
        self,
        file_path: str,
        task: str = "異常値検出"
    ) -> Dict[str, Any]:
        """
        Excel/CSVファイルをLLMで処理
        
        Args:
            file_path: ファイルパス
            task: 処理タスク（異常値検出、集計分析、ミス検出など）
            
        Returns:
            処理結果
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Excel/LLM処理が利用できません"
            }
        
        try:
            # ファイルを読み込む
            df = self.processor.load_file(file_path)
            
            # LLMで処理
            result = self.processor.process_with_llm(df, task)
            
            if result["success"]:
                # 結果をファイルに保存
                output_path = Path(file_path).stem + "_llm_analysis.txt"
                output_full_path = Path(file_path).parent / output_path
                
                with open(output_full_path, 'w', encoding='utf-8') as f:
                    f.write(result["response"])
                
                return {
                    "success": True,
                    "response": result["response"],
                    "model": result.get("model", self.model),
                    "output_file": str(output_full_path),
                    "rows": len(df),
                    "columns": len(df.columns)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "LLM処理に失敗しました")
                }
        except Exception as e:
            logger.error(f"Excel/LLM処理エラー: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_summary(self, file_path: str) -> Dict[str, Any]:
        """
        ファイルの要約を取得（LLMを使わずに）
        
        Args:
            file_path: ファイルパス
            
        Returns:
            要約情報
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Excel/LLM処理が利用できません"
            }
        
        try:
            df = self.processor.load_file(file_path)
            summary = self.processor.get_summary(df)
            
            return {
                "success": True,
                "summary": summary,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            }
        except Exception as e:
            logger.error(f"ファイル要約エラー: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
