#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ルーブリック読み込み・管理モジュール
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from manaos_logger import get_logger

logger = get_logger(__name__)


def load_rubric(rubric_file: str) -> Dict[str, Any]:
    """
    ルーブリックファイルを読み込む
    
    Args:
        rubric_file: ルーブリックファイルのパス
    
    Returns:
        ルーブリックデータ
    """
    rubric_path = Path(rubric_file)
    
    if not rubric_path.exists():
        # デフォルトパスを試す
        default_path = Path(__file__).parent / rubric_file
        if default_path.exists():
            rubric_path = default_path
        else:
            raise FileNotFoundError(f"Rubric file not found: {rubric_file}")
    
    with open(rubric_path, "r", encoding="utf-8") as f:
        rubric_data = yaml.safe_load(f)
    
    logger.info(f"Rubric loaded: {rubric_data.get('rubric', {}).get('total_items', 0)} items")
    return rubric_data


def get_rubric_items(rubric_data: Dict[str, Any]) -> Dict[str, list]:
    """
    ルーブリックの項目をカテゴリ別に取得
    
    Args:
        rubric_data: ルーブリックデータ
    
    Returns:
        カテゴリ別の項目リスト
    """
    rubric = rubric_data.get("rubric", {})
    
    items = {}
    for category in ["citations", "logic", "practicality", "completeness"]:
        category_data = rubric.get(category, {})
        items[category] = category_data.get("items", [])
    
    return items


def get_rubric_total_score(rubric_data: Dict[str, Any]) -> int:
    """
    ルーブリックの総合スコアを取得
    
    Args:
        rubric_data: ルーブリックデータ
    
    Returns:
        総合スコア
    """
    return rubric_data.get("rubric", {}).get("total_items", 20)


def get_rubric_min_pass_score(rubric_data: Dict[str, Any]) -> int:
    """
    ルーブリックの合格基準スコアを取得
    
    Args:
        rubric_data: ルーブリックデータ
    
    Returns:
        合格基準スコア
    """
    return rubric_data.get("rubric", {}).get("min_pass_score", 14)



