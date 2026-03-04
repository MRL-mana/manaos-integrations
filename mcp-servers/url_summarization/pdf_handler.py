#!/usr/bin/env python3
"""
PDF処理モジュール
PDFからテキスト抽出、OCR対応
"""

import PyPDF2
import pdfplumber
from typing import Dict


class PDFHandler:
    """PDF処理"""
    
    def process(self, pdf_path: str) -> Dict:
        """PDFを処理してテキスト抽出"""
        try:
            # PyPDF2でテキスト抽出
            text_pypdf2 = self._extract_with_pypdf2(pdf_path)
            
            # pdfplumberでテキスト抽出（より高精度）
            text_plumber = self._extract_with_plumber(pdf_path)
            
            # メタデータ取得
            metadata = self._get_metadata(pdf_path)
            
            # より良い結果を選択
            text = text_plumber if len(text_plumber) > len(text_pypdf2) else text_pypdf2
            
            return {
                "success": True,
                "text": text,
                "metadata": metadata,
                "word_count": len(text.split()),
                "page_count": metadata.get("num_pages", 0)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """PyPDF2でテキスト抽出"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except IOError:
            return ""
    
    def _extract_with_plumber(self, pdf_path: str) -> str:
        """pdfplumberでテキスト抽出"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except IOError:
            return ""
    
    def _get_metadata(self, pdf_path: str) -> Dict:
        """PDFメタデータ取得"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata or {}
                
                return {
                    "title": metadata.get('/Title', ''),
                    "author": metadata.get('/Author', ''),
                    "subject": metadata.get('/Subject', ''),
                    "creator": metadata.get('/Creator', ''),
                    "producer": metadata.get('/Producer', ''),
                    "num_pages": len(reader.pages)
                }
        except Exception:
            return {}


