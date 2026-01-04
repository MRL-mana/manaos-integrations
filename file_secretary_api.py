#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 File Secretary - API Server
Flask API実装
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from file_secretary_error_handler import retry_on_error, safe_database_operation

from file_secretary_db import FileSecretaryDB
from file_secretary_indexer import FileIndexer
from file_secretary_drive_indexer import GoogleDriveIndexer
from file_secretary_organizer import FileOrganizer
from file_secretary_ocr import FileSecretaryOCR
from file_secretary_schemas import FileSource, FileStatus, FileType
from file_secretary_templates import (
    parse_command, extract_search_query,
    template_inbox_status, template_done, template_restore,
    template_search, template_error, template_new_files
)

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("FileSecretaryAPI")
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# データベースとワーカー初期化
db_path = os.getenv("FILE_SECRETARY_DB_PATH", "file_secretary.db")
db = FileSecretaryDB(db_path)

# Indexer（監視は後で開始）
indexers: Dict[str, FileIndexer] = {}
drive_indexer: Optional[GoogleDriveIndexer] = None

# Organizer
organizer = FileOrganizer(db)

# OCR
ocr_engine = FileSecretaryOCR(db)


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "File Secretary",
        "version": "1.0.0"
    })


@app.route('/api/inbox/watch', methods=['POST'])
def watch_inbox():
    """INBOX監視開始"""
    try:
        data = request.get_json() or {}
        source_str = data.get("source", "mother")
        path = data.get("path")
        enabled = data.get("enabled", True)
        
        if not path:
            return jsonify({
                "status": "error",
                "error": "path is required"
            }), 400
        
        source = FileSource(source_str)
        
        if source.value in indexers:
            return jsonify({
                "status": "error",
                "error": f"既に監視中です: {source.value}"
            }), 400
        
        indexer = FileIndexer(db, source, path)
        
        if enabled:
            indexer.start_watching()
            # 既存ファイルもインデックス
            indexer.index_directory()
        
        indexers[source.value] = indexer
        
        return jsonify({
            "status": "success",
            "watch_id": f"watch_{source.value}_001",
            "source": source.value,
            "path": path,
            "enabled": enabled
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/inbox/watch"},
            user_message="INBOX監視開始に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/index', methods=['POST'])
def index_file():
    """ファイル索引作成"""
    try:
        data = request.get_json() or {}
        source_str = data.get("source", "mother")
        path = data.get("path")
        force = data.get("force", False)
        
        if not path:
            return jsonify({
                "status": "error",
                "error": "path is required"
            }), 400
        
        source = FileSource(source_str)
        file_path = Path(path)
        
        if not file_path.exists():
            return jsonify({
                "status": "error",
                "error": f"ファイルが存在しません: {path}"
            }), 404
        
        # Indexerを取得または作成
        if source.value not in indexers:
            indexer = FileIndexer(db, source, str(file_path.parent))
            indexers[source.value] = indexer
        else:
            indexer = indexers[source.value]
        
        file_record = indexer.index_file(file_path, force=force)
        
        if file_record:
            return jsonify({
                "status": "success",
                "file_record": file_record.to_dict()
            })
        else:
            return jsonify({
                "status": "error",
                "error": "ファイルインデックスに失敗しました"
            }), 500
            
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/files/index"},
            user_message="ファイル索引作成に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/inbox/status', methods=['GET'])
def get_inbox_status():
    """INBOX状況取得"""
    try:
        source_str = request.args.get("source")
        status_str = request.args.get("status")
        days = int(request.args.get("days", 1))
        
        source = FileSource(source_str) if source_str else None
        
        status_data = db.get_inbox_status(source=source, days_new=days, days_old=7)
        
        # 候補ファイル取得
        candidates = db.get_candidates(limit=3)
        candidates_dict = [fr.to_dict() for fr in candidates]
        
        # サマリ生成（簡易版）
        by_type = status_data.get("by_type", {})
        summary_parts = []
        for type_name, count in by_type.items():
            type_labels = {
                "pdf": "日報っぽい",
                "image": "画像素材",
                "xlsx": "データ",
                "other": "その他"
            }
            label = type_labels.get(type_name, type_name)
            summary_parts.append(f"{label}{count}")
        summary = "、".join(summary_parts) if summary_parts else "なし"
        
        return jsonify({
            "status": "success",
            "summary": status_data,
            "candidates": candidates_dict,
            "summary_text": summary
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/inbox/status"},
            user_message="INBOX状況取得に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/organize', methods=['POST'])
def organize_files():
    """ファイル整理実行"""
    try:
        data = request.get_json() or {}
        targets = data.get("targets", [])
        thread_ref = data.get("thread_ref")
        user = data.get("user")
        auto_tag = data.get("auto_tag", True)
        auto_alias = data.get("auto_alias", True)
        
        result = organizer.organize_files(
            file_ids=targets,
            thread_ref=thread_ref,
            user=user,
            auto_tag=auto_tag,
            auto_alias=auto_alias
        )
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/files/organize"},
            user_message="ファイル整理に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/restore', methods=['POST'])
def restore_files():
    """ファイル復元"""
    try:
        data = request.get_json() or {}
        targets = data.get("targets", [])
        user = data.get("user")
        
        result = organizer.restore_files(
            file_ids=targets if targets else None,
            user=user
        )
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/files/restore"},
            user_message="ファイル復元に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/search', methods=['GET'])
def search_files():
    """ファイル検索"""
    try:
        query = request.args.get("query")
        source_str = request.args.get("source")
        status_str = request.args.get("status")
        limit = int(request.args.get("limit", 10))
        
        if not query:
            return jsonify({
                "status": "error",
                "error": "query is required"
            }), 400
        
        # 全文検索
        results = db.search_files(query, limit=limit)
        
        # フィルタリング
        if source_str:
            source = FileSource(source_str)
            results = [fr for fr in results if fr.source == source]
        
        if status_str:
            status = FileStatus(status_str)
            results = [fr for fr in results if fr.status == status]
        
        return jsonify({
            "status": "success",
            "count": len(results),
            "results": [fr.to_dict() for fr in results]
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/files/search"},
            user_message="ファイル検索に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/<file_id>', methods=['GET'])
def get_file(file_id: str):
    """ファイル詳細取得"""
    try:
        file_record = db.get_file_record(file_id)
        
        if not file_record:
            return jsonify({
                "status": "error",
                "error": "ファイルが見つかりませんでした"
            }), 404
        
        return jsonify({
            "status": "success",
            "file_record": file_record.to_dict()
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": f"/api/files/{file_id}"},
            user_message="ファイル詳細取得に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/files/ocr', methods=['POST'])
def run_ocr():
    """OCR実行"""
    try:
        data = request.get_json() or {}
        file_id = data.get("file_id")
        
        if not file_id:
            return jsonify({
                "status": "error",
                "error": "file_id is required"
            }), 400
        
        file_record = db.get_file_record(file_id)
        if not file_record:
            return jsonify({
                "status": "error",
                "error": "ファイルが見つかりませんでした"
            }), 404
        
        ocr_ref = ocr_engine.run_ocr(file_record)
        
        if ocr_ref:
            return jsonify({
                "status": "success",
                "ocr_text_ref": ocr_ref,
                "file_id": file_id
            })
        else:
            return jsonify({
                "status": "error",
                "error": "OCR実行に失敗しました"
            }), 500
            
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/files/ocr"},
            user_message="OCR実行に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/reports/weekly', methods=['POST'])
def generate_weekly_report():
    """週報生成"""
    try:
        from file_secretary_sheets import FileSecretarySheets
        
        sheets = FileSecretarySheets(db)
        report_data = sheets.generate_weekly_report()
        
        # Slackに送信（オプション）
        send_to_slack = request.get_json() or {}
        if send_to_slack.get("send_to_slack", False):
            sheets.send_to_slack(report_data)
        
        return jsonify({
            "status": "success",
            "report": report_data
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reports/weekly"},
            user_message="週報生成に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/images/coupon', methods=['POST'])
def generate_coupon():
    """クーポン画像生成"""
    try:
        from file_secretary_image_templates import FileSecretaryImageTemplates
        
        data = request.get_json() or {}
        coupon_type = data.get("coupon_type", "洗車")
        discount = data.get("discount")
        
        templates = FileSecretaryImageTemplates()
        result = templates.generate_coupon(coupon_type, discount)
        
        if result:
            return jsonify({
                "status": "success",
                "result": result
            })
        else:
            return jsonify({
                "status": "error",
                "error": "クーポン画像生成に失敗しました"
            }), 500
            
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/images/coupon"},
            user_message="クーポン画像生成に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/slack/handle', methods=['POST'])
def handle_slack():
    """Slack統合エンドポイント"""
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        user = data.get("user", "unknown")
        channel = data.get("channel", "general")
        thread_ts = data.get("thread_ts")
        files = data.get("files", [])
        
        if not text:
            return jsonify({
                "status": "error",
                "error": "text is required"
            }), 400
        
        # コマンド解析
        command = parse_command(text)
        
        if command == "status":
            # INBOX状況取得
            status_data = db.get_inbox_status()
            candidates = db.get_candidates(limit=3)
            
            response_text = template_inbox_status(
                new_count=status_data["new_count"],
                old_count=status_data["old_count"],
                long_term_count=status_data["long_term_count"],
                summary=status_data.get("summary_text", "なし"),
                candidates=[fr.to_dict() for fr in candidates]
            )
            
        elif command == "done":
            # 整理実行
            result = organizer.organize_files(
                file_ids=[],
                thread_ref=thread_ts,
                user=user,
                auto_tag=True,
                auto_alias=True
            )
            
            if result["status"] == "success":
                response_text = template_done(result["files"])
            else:
                response_text = template_error(result.get("error", "整理に失敗しました"))
                
        elif command == "restore":
            # 復元
            result = organizer.restore_files(
                file_ids=None,
                user=user
            )
            
            if result["status"] == "success":
                response_text = template_restore(result["files"])
            else:
                response_text = template_error(result.get("error", "復元に失敗しました"))
                
        elif command == "search":
            # 検索（OCRテキストも検索）
            query = extract_search_query(text) or text
            results = db.search_files(query, limit=5)
            
            # OCRテキスト内も検索
            ocr_matched = ocr_engine.search_in_ocr_text(query, results)
            if ocr_matched:
                results.extend(ocr_matched)
            
            response_text = template_search(query, [fr.to_dict() for fr in results[:5]])
            
        else:
            response_text = template_error("そのコマンドは分からなかった")
        
        return jsonify({
            "status": "success",
            "response_text": response_text,
            "response_type": "thread"
        })
        
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/slack/handle"},
            user_message="Slack処理に失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e),
            "response_text": template_error("処理中にエラーが発生しました")
        }), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5120))
    logger.info(f"🔌 File Secretary API起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")


