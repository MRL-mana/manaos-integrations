#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research API Server
"""

import json
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

from step_deep_research.orchestrator import StepDeepResearchOrchestrator
from manaos_logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)

# グローバルインスタンス
orchestrator = None


def init_orchestrator():
    """オーケストレーターを初期化"""
    global orchestrator
    if orchestrator is None:
        config_path = Path("step_deep_research_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        orchestrator = StepDeepResearchOrchestrator(config)
    return orchestrator


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "Step-Deep-Research"})


@app.route('/research', methods=['POST'])
def create_research():
    """調査ジョブ作成"""
    try:
        data = request.get_json()
        user_query = data.get("query", "")
        
        if not user_query:
            return jsonify({"error": "query is required"}), 400
        
        orchestrator = init_orchestrator()
        job_id = orchestrator.create_job(user_query)
        
        return jsonify({
            "job_id": job_id,
            "status": "created",
            "message": "Research job created"
        }), 201
        
    except Exception as e:
        logger.error(f"Create research error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/research/<job_id>', methods=['POST'])
def execute_research(job_id):
    """調査ジョブ実行"""
    try:
        orchestrator = init_orchestrator()
        result = orchestrator.execute_job(job_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Execute research error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/research/<job_id>/status', methods=['GET'])
def get_research_status(job_id):
    """調査ジョブステータス取得"""
    try:
        orchestrator = init_orchestrator()
        status = orchestrator.get_job_status(job_id)
        
        if not status:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Get status error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    init_orchestrator()
    app.run(host='0.0.0.0', port=5120, debug=True)



