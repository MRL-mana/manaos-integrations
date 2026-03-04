"""
n8n連携機能を統合APIサーバーに追加するスクリプト
画像生成完了時にn8n Webhookを呼び出す機能を追加
"""

import os
import requests
from typing import Optional, Dict, Any

def add_n8n_notification_to_comfyui_generate():
    """
    ComfyUI画像生成エンドポイントにn8n通知機能を追加
    """
    code = '''
@app.route("/api/comfyui/generate", methods=["POST"])
def comfyui_generate():
    """ComfyUIで画像生成"""
    data = request.json
    prompt = data.get("prompt", "")
    negative_prompt = data.get("negative_prompt", "")
    width = data.get("width", 512)
    height = data.get("height", 512)
    steps = data.get("steps", 20)
    cfg_scale = data.get("cfg_scale", 7.0)
    seed = data.get("seed", -1)
    
    comfyui = integrations.get("comfyui")
    if not comfyui or not comfyui.is_available():
        return jsonify({"error": "ComfyUIが利用できません"}), 503
    
    prompt_id = comfyui.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        seed=seed
    )
    
    if prompt_id:
        # n8n Webhookに通知（オプション）
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url:
            try:
                requests.post(n8n_webhook_url, json={
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                    "status": "generated",
                    "timestamp": datetime.now().isoformat()
                }, timeout=5)
                logger.info(f"n8n Webhookに通知を送信しました: {prompt_id}")
            except Exception as e:
                logger.warning(f"n8n Webhook通知に失敗: {e}")
        
        return jsonify({"prompt_id": prompt_id, "status": "success"})
    else:
        return jsonify({"error": "画像生成に失敗しました"}), 500
'''
    return code

def create_n8n_workflow_template():
    """
    n8nワークフローのテンプレートJSONを作成
    """
    workflow = {
        "name": "ManaOS Image Generation Workflow",
        "nodes": [
            {
                "parameters": {},
                "id": "webhook-trigger",
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300],
                "webhookId": "comfyui-generated"
            },
            {
                "parameters": {
                    "operation": "upload",
                    "name": "={{ $json.prompt_id }}.png",
                    "binaryData": True
                },
                "id": "google-drive-upload",
                "name": "Google Drive Upload",
                "type": "n8n-nodes-base.googleDrive",
                "typeVersion": 2,
                "position": [450, 300]
            },
            {
                "parameters": {
                    "operation": "create",
                    "name": "画像生成_{{ $now.toISO() }}.md",
                    "content": "= 画像生成: {{ $json.prompt }}\n\n- 生成日時: {{ $json.timestamp }}\n- プロンプト: {{ $json.prompt }}\n- Google Drive: [リンク]"
                },
                "id": "obsidian-create",
                "name": "Obsidian Create",
                "type": "n8n-nodes-base.obsidian",
                "typeVersion": 1,
                "position": [650, 300]
            },
            {
                "parameters": {
                    "channel": "#manaos-notifications",
                    "text": "🎨 画像生成完了\n\nプロンプト: {{ $json.prompt }}\n生成ID: {{ $json.prompt_id }}"
                },
                "id": "slack-notify",
                "name": "Slack Notify",
                "type": "n8n-nodes-base.slack",
                "typeVersion": 1,
                "position": [850, 300]
            }
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Google Drive Upload", "type": "main", "index": 0}]]
            },
            "Google Drive Upload": {
                "main": [[{"node": "Obsidian Create", "type": "main", "index": 0}]]
            },
            "Obsidian Create": {
                "main": [[{"node": "Slack Notify", "type": "main", "index": 0}]]
            }
        }
    }
    return workflow

if __name__ == "__main__":
    print("n8n連携機能の追加方法:")
    print("1. unified_api_server.pyのcomfyui_generate関数を上記のコードに置き換え")
    print("2. n8nワークフローのテンプレートJSONをn8nにインポート")
    print("3. 環境変数N8N_WEBHOOK_URLを設定")


















