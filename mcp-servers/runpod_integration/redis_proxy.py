#!/usr/bin/env python3
"""
Redis Proxy Server
RunPodからこのはサーバーのRedisにアクセスするためのHTTPプロキシ
"""

import os
from flask import Flask, request, jsonify
import redis
import json
import uuid
from datetime import datetime

app = Flask(__name__)

# Redis接続
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    try:
        redis_client.ping()
        return jsonify({
            "status": "ok",
            "redis_connected": True,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "redis_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/queue/length', methods=['GET'])
def queue_length():
    """キュー長取得"""
    try:
        queue_name = request.args.get('queue', 'manaos:gpu:jobs')
        length = redis_client.llen(queue_name)
        return jsonify({
            "queue_name": queue_name,
            "length": length,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/job/submit', methods=['POST'])
def submit_job():
    """ジョブ投入"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # ジョブID生成
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Redisに投入
        queue_name = data.get('queue', 'manaos:gpu:jobs')
        redis_client.lpush(queue_name, json.dumps(job_data))
        
        return jsonify({
            "job_id": job_id,
            "status": "submitted",
            "queue": queue_name,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/job/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """ジョブステータス取得"""
    try:
        status = redis_client.get(f"manaos:gpu:results:{job_id}:status")
        if status:
            return jsonify({
                "job_id": job_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "job_id": job_id,
                "status": "not_found",
                "timestamp": datetime.now().isoformat()
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/job/result/<job_id>', methods=['GET'])
def get_job_result(job_id):
    """ジョブ結果取得"""
    try:
        result = redis_client.get(f"manaos:gpu:results:{job_id}:result")
        if result:
            return jsonify({
                "job_id": job_id,
                "result": json.loads(result),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "job_id": job_id,
                "result": None,
                "timestamp": datetime.now().isoformat()
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/job/error/<job_id>', methods=['GET'])
def get_job_error(job_id):
    """ジョブエラー取得"""
    try:
        error = redis_client.get(f"manaos:gpu:results:{job_id}:error")
        if error:
            return jsonify({
                "job_id": job_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "job_id": job_id,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Redis Proxy Server Starting...")
    print("📡 RunPodからHTTP経由でRedisにアクセス可能")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
