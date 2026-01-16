#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テンプレートルーター
Intentに応じて適切なテンプレートを選択
"""

import re
from typing import Dict, Any, Optional
from pathlib import Path

from manaos_logger import get_logger
from .utils import load_prompt_template

logger = get_logger(__name__)


class TemplateRouter:
    """テンプレートルーター"""
    
    def __init__(self):
        """初期化"""
        self.templates = {
            "technical_selection": "step_deep_research/templates/technical_selection_template.md",
            "troubleshooting": "step_deep_research/templates/troubleshooting_template.md",
            "latest_trends": "step_deep_research/templates/latest_trends_template.md",
            "default": "step_deep_research/templates/report_template.md"
        }
    
    def detect_template_type(self, query: str) -> str:
        """
        クエリからテンプレートタイプを検出
        
        Args:
            query: ユーザークエリ
        
        Returns:
            テンプレートタイプ
        """
        query_lower = query.lower()
        
        # 技術選定パターン
        selection_keywords = [
            "比較", "選定", "どちら", "どっち", "どれ", "選択",
            "メリデメ", "メリットデメリット", "比較して", "選んで"
        ]
        if any(keyword in query_lower for keyword in selection_keywords):
            return "technical_selection"
        
        # トラブル調査パターン
        troubleshooting_keywords = [
            "エラー", "問題", "不具合", "動かない", "失敗", "原因",
            "対処", "解決", "直して", "どうして", "なぜ"
        ]
        if any(keyword in query_lower for keyword in troubleshooting_keywords):
            return "troubleshooting"
        
        # 最新動向パターン
        latest_keywords = [
            "最新", "新機能", "変更点", "アップデート", "動向",
            "2026", "2025", "最新版", "新バージョン"
        ]
        if any(keyword in query_lower for keyword in latest_keywords):
            return "latest_trends"
        
        return "default"
    
    def get_template(self, template_type: Optional[str] = None, query: Optional[str] = None) -> str:
        """
        テンプレートを取得
        
        Args:
            template_type: テンプレートタイプ（指定時はそのまま使用）
            query: ユーザークエリ（template_type未指定時は検出に使用）
        
        Returns:
            テンプレート内容
        """
        if template_type is None:
            if query is None:
                template_type = "default"
            else:
                template_type = self.detect_template_type(query)
        
        template_path = self.templates.get(template_type, self.templates["default"])
        
        try:
            return load_prompt_template(template_path)
        except Exception as e:
            logger.warning(f"Template load error: {e}, using default")
            return load_prompt_template(self.templates["default"])


