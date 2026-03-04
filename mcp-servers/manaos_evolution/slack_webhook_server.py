#!/usr/bin/env python3
"""
Slack Webhook Server for Voice Input
音声テキストを受信してn8nに転送
"""

from flask import Flask, request, jsonify
import requests
import os
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/voice-task')
SLACK_TOKEN = os.environ.get('SLACK_TOKEN', '')

@app.route('/webhook/voice-input', methods=['POST'])
def voice_input():
    """
    音声テキストを受信してn8nに転送
    """
    try:
        data = request.get_json()
        
        # リクエストデータの検証
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text field'}), 400
        
        text = data['text']
        user_id = data.get('user_id', 'unknown')
        source = data.get('source', 'shortcut')  # shortcut, slack, etc.
        
        logger.info(f"Voice input received: {text[:50]}... from {user_id} via {source}")
        
        # n8nに転送
        n8n_payload = {
            'text': text,
            'user_id': user_id,
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'raw_data': data
        }
        
        try:
            response = requests.post(
                N8N_WEBHOOK_URL,
                json=n8n_payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Forwarded to n8n: {response.status_code}")
            
            return jsonify({
                'status': 'success',
                'message': 'Voice input processed',
                'n8n_response': response.json() if response.content else None
            }), 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to forward to n8n: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to forward to n8n',
                'error': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing voice input: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'service': 'voice-input-webhook',
        'n8n_url': N8N_WEBHOOK_URL
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Starting Voice Input Webhook Server on port {port}")
    logger.info(f"N8N Webhook URL: {N8N_WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
