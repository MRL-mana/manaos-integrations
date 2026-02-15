#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーティリティ関数
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from unified_logging import get_service_logger
logger = get_service_logger("utils")


def load_prompt_template(template_path: str) -> str:
    """
    プロンプトテンプレートを読み込む
    
    Args:
        template_path: テンプレートファイルのパス
    
    Returns:
        テンプレート内容
    """
    template_file = Path(template_path)
    
    if not template_file.exists():
        # デフォルトパスを試す
        default_path = Path(__file__).parent / template_path
        if default_path.exists():
            template_file = default_path
        else:
            raise FileNotFoundError(f"Template file not found: {template_path}")
    
    with open(template_file, "r", encoding="utf-8") as f:
        return f.read()


def format_prompt(template: str, **kwargs) -> str:
    """
    プロンプトテンプレートをフォーマット
    
    Args:
        template: テンプレート文字列
        **kwargs: フォーマット用の変数
    
    Returns:
        フォーマット済みプロンプト
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing template variable: {e}")
        return template


def save_jsonl(data: Dict[str, Any], file_path: Path):
    """
    JSONL形式でデータを保存
    
    Args:
        data: 保存するデータ
        file_path: ファイルパス
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def load_jsonl(file_path: Path) -> list:
    """
    JSONL形式のファイルを読み込む
    
    Args:
        file_path: ファイルパス
    
    Returns:
        データのリスト
    """
    if not file_path.exists():
        return []
    
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    return data


def parse_yaml_response(response: str) -> Dict[str, Any]:
    """
    LLMのYAML形式レスポンスをパース
    
    Args:
        response: LLMのレスポンス
    
    Returns:
        パースされたデータ
    """
    # YAMLブロックを抽出
    if "```yaml" in response:
        start = response.find("```yaml") + 7
        end = response.find("```", start)
        yaml_content = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        yaml_content = response[start:end].strip()
    else:
        yaml_content = response.strip()
    
    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error: {e}")
        logger.debug(f"Response content: {response[:500]}")
        return {}


def parse_json_response(response: str) -> Dict[str, Any]:
    """
    LLMのJSON形式レスポンスをパース
    
    Args:
        response: LLMのレスポンス
    
    Returns:
        パースされたデータ
    """
    # JSONブロックを抽出
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        json_content = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        json_content = response[start:end].strip()
    else:
        json_content = response.strip()
    
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"Response content: {response[:500]}")
        return {}



