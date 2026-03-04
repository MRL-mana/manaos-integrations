#!/usr/bin/env python3
"""
ワークフロー自動化エンジン
n8n風のビジュアルワークフローを実行
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/workflow_automation")
WORKFLOWS_DIR = WORK_DIR / "workflows"
TEMPLATES_DIR = WORK_DIR / "templates"
RESULTS_DIR = WORK_DIR / "results"

for dir_path in [WORKFLOWS_DIR, TEMPLATES_DIR, RESULTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class WorkflowEngine:
    """ワークフロー実行エンジン"""
    
    def __init__(self):
        self.actions = {
            "manaos_v3": self.action_manaos_v3,
            "whisper_voice": self.action_whisper_voice,
            "x280_screenshot": self.action_x280_screenshot,
            "x280_gui_click": self.action_x280_gui_click,
            "line_notify": self.action_line_notify,
            "file_analyze": self.action_file_analyze,
            "wait": self.action_wait,
            "condition": self.action_condition,
        }
    
    def execute_workflow(self, workflow):
        """
        ワークフロー実行
        
        workflow format:
        {
          "name": "Workflow Name",
          "steps": [
            {
              "id": "step1",
              "action": "manaos_v3",
              "params": {"text": "今日の予定を教えて"},
              "next": "step2"
            },
            ...
          ]
        }
        """
        log(f"🚀 ワークフロー実行: {workflow.get('name', 'Unnamed')}")
        
        steps = workflow.get("steps", [])
        results = {}
        current_step_id = steps[0]["id"] if steps else None
        
        while current_step_id:
            step = next((s for s in steps if s["id"] == current_step_id), None)
            if not step:
                break
            
            log(f"  ステップ実行: {step['id']} - {step['action']}")
            
            action_func = self.actions.get(step["action"])
            if not action_func:
                log(f"  ❌ 未知のアクション: {step['action']}")
                break
            
            result = action_func(step.get("params", {}), results)
            results[step["id"]] = result
            
            # 次のステップ決定
            if "condition" in step:
                # 条件分岐
                condition_result = self.evaluate_condition(step["condition"], result)
                current_step_id = step.get("next_true") if condition_result else step.get("next_false")
            else:
                current_step_id = step.get("next")
        
        log(f"✅ ワークフロー完了: {workflow.get('name')}")
        
        return {
            "success": True,
            "workflow_name": workflow.get("name"),
            "steps_executed": len(results),
            "results": results
        }
    
    # ===== アクション実装 =====
    
    def action_manaos_v3(self, params, context):
        """ManaOS v3.0実行"""
        text = params.get("text", "")
        try:
            response = requests.post(
                "http://localhost:9200/v3/orchestrator/run",
                json={"text": text, "actor": "remi"},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def action_whisper_voice(self, params, context):
        """Whisper音声認識（※実際は音声ファイル必要）"""
        text = params.get("text", "")
        # テキスト実行モード
        return self.action_manaos_v3({"text": text}, context)
    
    def action_x280_screenshot(self, params, context):
        """X280スクリーンショット"""
        try:
            response = requests.post(
                "http://100.127.121.20:5009/screenshot",
                json=params,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def action_x280_gui_click(self, params, context):
        """X280 GUIクリック"""
        try:
            response = requests.post(
                "http://100.127.121.20:5009/mouse/click",
                json=params,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def action_line_notify(self, params, context):
        """LINE通知"""
        message = params.get("message", "")
        try:
            response = requests.post(
                "http://localhost:5015/send",
                json={"message": message},
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def action_file_analyze(self, params, context):
        """ファイル分析"""
        path = params.get("path", "")
        try:
            response = requests.post(
                "http://localhost:5016/analyze/file",
                json={"path": path},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def action_wait(self, params, context):
        """待機"""
        seconds = params.get("seconds", 1)
        time.sleep(seconds)
        return {"success": True, "waited_seconds": seconds}
    
    def action_condition(self, params, context):
        """条件判定"""
        # 前のステップの結果を評価
        return {"success": True, "evaluated": True}
    
    def evaluate_condition(self, condition, result):
        """条件評価"""
        # シンプルな条件評価
        if condition.get("type") == "success":
            return result.get("success", False)
        return True


# グローバルエンジン
engine = WorkflowEngine()


# ===== API エンドポイント =====

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Workflow Automation Engine",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/workflow/execute', methods=['POST'])
def execute_workflow():
    """ワークフロー実行"""
    try:
        workflow = request.json
        
        if not workflow or "steps" not in workflow:
            return jsonify({"success": False, "error": "無効なワークフロー"}), 400
        
        result = engine.execute_workflow(workflow)
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = RESULTS_DIR / f"result_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        log(f"❌ ワークフロー実行エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/workflow/save', methods=['POST'])
def save_workflow():
    """ワークフロー保存"""
    try:
        workflow = request.json
        name = workflow.get("name", "unnamed")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = WORKFLOWS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
        
        log(f"✅ ワークフロー保存: {filename}")
        
        return jsonify({
            "success": True,
            "filename": filename,
            "path": str(filepath)
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/workflow/list', methods=['GET'])
def list_workflows():
    """保存済みワークフロー一覧"""
    workflows = []
    for file_path in sorted(WORKFLOWS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            workflows.append({
                "filename": file_path.name,
                "name": data.get("name", "Unnamed"),
                "steps_count": len(data.get("steps", [])),
                "created": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    
    return jsonify({
        "success": True,
        "workflows": workflows
    })


@app.route('/templates/list', methods=['GET'])
def list_templates():
    """テンプレート一覧"""
    return jsonify({
        "success": True,
        "templates": [
            {
                "name": "daily_report",
                "description": "毎日のレポート送信",
                "steps": 3
            },
            {
                "name": "backup_workflow",
                "description": "X280→Drive自動バックアップ",
                "steps": 4
            },
            {
                "name": "monitoring_alert",
                "description": "監視＋アラート",
                "steps": 5
            }
        ]
    })


if __name__ == '__main__':
    log("=" * 60)
    log("⚡ ワークフロー自動化エンジン起動")
    log("=" * 60)
    log("API起動中... (http://0.0.0.0:5017)")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=5017, debug=os.getenv("DEBUG", "False").lower() == "true")

