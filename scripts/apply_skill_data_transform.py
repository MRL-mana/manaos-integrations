#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データ変換処理スクリプト
YAML形式のデータ変換設定を読み込み、CSV/JSON/Excel形式の変換を実行
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# pandasのインポート（オプション）
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_data_transform_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def read_data(file_path: Path, file_format: str) -> Optional[pd.DataFrame]:
    """データを読み込む"""
    if not PANDAS_AVAILABLE:
        return None
    
    try:
        if file_format == "csv":
            return pd.read_csv(file_path, encoding='utf-8')
        elif file_format == "json":
            return pd.read_json(file_path, encoding='utf-8')
        elif file_format == "excel":
            return pd.read_excel(file_path)
        else:
            return None
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return None


def write_data(df: pd.DataFrame, file_path: Path, file_format: str) -> bool:
    """データを書き込む"""
    if not PANDAS_AVAILABLE:
        return False
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_format == "csv":
            df.to_csv(file_path, index=False, encoding='utf-8')
        elif file_format == "json":
            df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        elif file_format == "excel":
            df.to_excel(file_path, index=False)
        else:
            return False
        
        return True
    except Exception as e:
        print(f"❌ ファイル書き込みエラー: {e}")
        return False


def apply_transformations(df: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
    """変換ルールを適用"""
    if not PANDAS_AVAILABLE:
        return df
    
    result_df = df.copy()
    
    for transform in transformations:
        transform_type = transform.get("type", "")
        
        if transform_type == "filter":
            # 簡易フィルタ（実際の実装ではより高度な条件が必要）
            condition = transform.get("condition", "")
            if condition:
                try:
                    # 簡易実装：条件式の評価（実際の実装ではより安全な方法が必要）
                    result_df = result_df.query(condition)
                except Exception as e:
                    print(f"⚠️  フィルタエラー: {e}")
        
        elif transform_type == "format":
            date_format = transform.get("date_format")
            if date_format:
                # 日付カラムをフォーマット（実装簡略化）
                pass
        
        elif transform_type == "sort":
            columns = transform.get("columns", [])
            ascending = transform.get("ascending", True)
            if columns:
                result_df = result_df.sort_values(by=columns, ascending=ascending)
        
        elif transform_type == "rename":
            columns_map = transform.get("columns", {})
            if columns_map:
                result_df = result_df.rename(columns=columns_map)
    
    return result_df


def clean_data(df: pd.DataFrame, cleaning_rules: Dict[str, Any]) -> pd.DataFrame:
    """データをクリーニング"""
    if not PANDAS_AVAILABLE:
        return df
    
    result_df = df.copy()
    
    if cleaning_rules.get("remove_empty"):
        result_df = result_df.dropna(how='all')
    
    if cleaning_rules.get("remove_duplicates"):
        result_df = result_df.drop_duplicates()
    
    if cleaning_rules.get("trim_whitespace"):
        # 文字列カラムの空白をトリム
        for col in result_df.select_dtypes(include=['object']).columns:
            result_df[col] = result_df[col].str.strip()
    
    return result_df


def convert_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """データを変換"""
    if not PANDAS_AVAILABLE:
        return {"success": False, "error": "pandasがインストールされていません"}
    
    input_file = Path(data.get("input_file", ""))
    output_file = Path(data.get("output_file", ""))
    input_format = data.get("input_format", "")
    output_format = data.get("output_format", "")
    
    if not input_file.exists():
        return {"success": False, "error": f"入力ファイルが見つかりません: {input_file}"}
    
    # データ読み込み
    df = read_data(input_file, input_format)
    if df is None:
        return {"success": False, "error": "データ読み込みに失敗しました"}
    
    original_count = len(df)
    
    # 変換ルールを適用
    transformations = data.get("transformation", [])
    if transformations:
        df = apply_transformations(df, transformations)
    
    # データ書き込み
    if not write_data(df, output_file, output_format):
        return {"success": False, "error": "データ書き込みに失敗しました"}
    
    return {
        "success": True,
        "input_rows": original_count,
        "output_rows": len(df),
        "output_file": str(output_file)
    }


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "convert": "データ変換",
            "clean": "データクリーニング",
            "format": "フォーマット変換"
        }
        action_name = action_names.get(action, action)
        
        message = f"📊 *データ変換: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "input_rows" in result:
                message += f"入力行数: {result['input_rows']}\n"
            if "output_rows" in result:
                message += f"出力行数: {result['output_rows']}\n"
            if "output_file" in result:
                message += f"出力ファイル: {result['output_file']}\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Data Transform",
            "icon_emoji": ":chart_with_upwards_trend:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "data_transform":
        print("⚠️  kindが'data_transform'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "convert":
            result = convert_data(data)
        else:
            result = {"success": False, "error": f"未実装のアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_data_transform.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
