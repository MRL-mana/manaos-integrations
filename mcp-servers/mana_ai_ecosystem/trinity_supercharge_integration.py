#!/usr/bin/env python3
"""
🚀 Trinity Supercharge Integration for ManaOS
トリニティ・スーパーチャージをManaOSに統合
"""

import json
import logging
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Trinity Automationモジュールへのパスを追加
sys.path.insert(0, '/root/trinity_automation')

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TrinitySuperchargeIntegration')

class TrinitySuperchargeIntegration:
    """Trinity SuperchargeのManaOS統合クラス"""
    
    def __init__(self):
        self.trinity_automation_path = Path('/root/trinity_automation')
        self.services = {
            "voice_assistant": {
                "name": "🎤 音声アシスタント",
                "description": "音声認識・音声合成でハンズフリー操作",
                "command": "trinity_voice_assistant.py",
                "category": "interaction"
            },
            "smart_scheduler": {
                "name": "📅 スマートスケジューラー",
                "description": "定期タスク自動実行・時間指定・カレンダー連携",
                "command": "trinity_smart_scheduler.py",
                "category": "automation"
            },
            "multi_ai": {
                "name": "🤖 マルチAI統合",
                "description": "Claude/GPT/Gemini自動切り替え・最適化",
                "command": "trinity_multi_ai.py",
                "category": "ai"
            },
            "auto_notes": {
                "name": "📝 自動ノート作成",
                "description": "Obsidian連携・自動タグ付け・検索",
                "command": "trinity_auto_notes.py",
                "category": "productivity"
            },
            "smart_backup": {
                "name": "💾 インテリジェントバックアップ",
                "description": "差分バックアップ・Google Drive連携・バージョン管理",
                "command": "trinity_smart_backup.py",
                "category": "data"
            },
            "unified_dashboard": {
                "name": "🎨 統合Webダッシュボード",
                "description": "全システム統合UI・リアルタイム表示",
                "command": "trinity_unified_dashboard.py",
                "port": 5009,
                "category": "interface"
            },
            "notification_system": {
                "name": "🔔 通知システム",
                "description": "Slack/Discord/メール通知・カスタムアラート",
                "command": "trinity_notification_system.py",
                "category": "communication"
            },
            "file_watcher": {
                "name": "👀 ファイル監視システム",
                "description": "リアルタイム監視・自動処理・同期",
                "command": "trinity_file_watcher.py",
                "category": "automation"
            },
            "secure_api": {
                "name": "🌐 セキュアリモートAPI",
                "description": "認証・暗号化・APIキー管理",
                "command": "trinity_secure_api.py",
                "port": 5010,
                "category": "security"
            },
            "analytics_dashboard": {
                "name": "📊 分析ダッシュボード",
                "description": "パフォーマンス可視化・ログ分析・統計",
                "command": "trinity_analytics_dashboard.py",
                "port": 5011,
                "category": "monitoring"
            }
        }
        
        # ManaOS統合情報
        self.mana_os_integration = {
            "version": "1.0.0",
            "integrated_at": datetime.now().isoformat(),
            "base_path": str(self.trinity_automation_path),
            "total_features": len(self.services)
        }
        
        logger.info("🚀 Trinity Supercharge Integration 初期化完了")
    
    def get_service_status(self, service_id: str) -> Dict:
        """サービスのステータスを取得"""
        service = self.services.get(service_id)
        if not service:
            return {"error": "Service not found"}
        
        # プロセス確認
        try:
            result = subprocess.run(
                ['pgrep', '-f', service['command']],
                capture_output=True,
                text=True
            )
            is_running = bool(result.stdout.strip())
            
            status = {
                "service_id": service_id,
                "name": service['name'],
                "description": service['description'],
                "category": service['category'],
                "status": "running" if is_running else "stopped",
                "command": service['command']
            }
            
            # Webサービスの場合、URL情報を追加
            if 'port' in service:
                status['port'] = service['port']
                status['url'] = f"http://localhost:{service['port']}"
                status['external_url'] = f"http://163.44.120.49:{service['port']}"
            
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_services_status(self) -> List[Dict]:
        """全サービスのステータスを取得"""
        return [self.get_service_status(sid) for sid in self.services.keys()]
    
    def execute_service_action(self, service_id: str, action: str, **kwargs) -> Dict:
        """サービスのアクションを実行"""
        service = self.services.get(service_id)
        if not service:
            return {"success": False, "error": "Service not found"}
        
        script_path = self.trinity_automation_path / service['command']
        
        try:
            if action == "start":
                # サービス起動
                cmd = ['python3', str(script_path)]
                if service_id == "smart_scheduler":
                    cmd.append('--run')
                elif service_id == "file_watcher":
                    cmd.append('--run')
                elif service_id == "voice_assistant":
                    cmd.append('--listen')
                
                subprocess.Popen(cmd, cwd=str(self.trinity_automation_path))
                return {"success": True, "message": f"{service['name']} を起動しました"}
            
            elif action == "stop":
                # サービス停止
                result = subprocess.run(
                    ['pkill', '-f', service['command']],
                    capture_output=True
                )
                return {"success": True, "message": f"{service['name']} を停止しました"}
            
            elif action == "status":
                return self.get_service_status(service_id)
            
            # サービス固有のアクション
            elif service_id == "auto_notes" and action == "create":
                title = kwargs.get('title', 'New Note')
                content = kwargs.get('content', '')
                result = subprocess.run(
                    ['python3', str(script_path), '--create', title, content],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return {"success": True, "output": result.stdout}
            
            elif service_id == "smart_backup" and action == "create":
                name = kwargs.get('name', 'manual')
                result = subprocess.run(
                    ['python3', str(script_path), '--create', name],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                return {"success": True, "output": result.stdout}
            
            elif service_id == "smart_scheduler" and action == "list":
                result = subprocess.run(
                    ['python3', str(script_path), '--list'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return {"success": True, "output": result.stdout}
            
            elif service_id == "notification_system" and action == "send":
                message = kwargs.get('message', '')
                level = kwargs.get('level', 'info')
                result = subprocess.run(
                    ['python3', str(script_path), '--notify', message, level],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return {"success": True, "output": result.stdout}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_quick_actions(self) -> List[Dict]:
        """ManaOS用クイックアクション一覧"""
        return [
            {
                "id": "backup_now",
                "name": "💾 今すぐバックアップ",
                "description": "重要ファイルをバックアップ",
                "service": "smart_backup",
                "action": "create"
            },
            {
                "id": "create_note",
                "name": "📝 ノート作成",
                "description": "新しいノートを作成",
                "service": "auto_notes",
                "action": "create"
            },
            {
                "id": "check_schedule",
                "name": "📅 スケジュール確認",
                "description": "予定タスク一覧",
                "service": "smart_scheduler",
                "action": "list"
            },
            {
                "id": "send_notification",
                "name": "🔔 通知送信",
                "description": "テスト通知を送信",
                "service": "notification_system",
                "action": "send"
            },
            {
                "id": "open_dashboard",
                "name": "🎨 ダッシュボード",
                "description": "統合ダッシュボードを開く",
                "url": "http://localhost:5009"
            },
            {
                "id": "open_analytics",
                "name": "📊 分析画面",
                "description": "分析ダッシュボードを開く",
                "url": "http://localhost:5011"
            }
        ]
    
    def get_categories(self) -> Dict[str, List[str]]:
        """カテゴリ別サービス一覧"""
        categories = {}
        for service_id, service in self.services.items():
            category = service['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(service_id)
        return categories
    
    def get_web_services(self) -> List[Dict]:
        """Webサービス一覧"""
        web_services = []
        for service_id, service in self.services.items():
            if 'port' in service:
                web_services.append({
                    "service_id": service_id,
                    "name": service['name'],
                    "port": service['port'],
                    "url": f"http://localhost:{service['port']}",
                    "external_url": f"http://163.44.120.49:{service['port']}",
                    "tailscale_url": f"http://100.93.120.33:{service['port']}"
                })
        return web_services
    
    def call_secure_api(self, endpoint: str, method: str = "GET", 
                       api_key: Optional[str] = None, data: Optional[Dict] = None) -> Dict:
        """セキュアAPIを呼び出し"""
        try:
            # APIキーを設定ファイルから取得
            if not api_key:
                api_keys_path = self.trinity_automation_path / 'configs' / 'api_keys.json'
                if api_keys_path.exists():
                    with open(api_keys_path, 'r') as f:
                        keys_data = json.load(f)
                        api_key = keys_data['keys']['master']['key']
            
            url = f"http://localhost:5010/api/{endpoint}"
            headers = {'X-API-Key': api_key} if api_key else {}
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, json=data)
            else:
                return {"success": False, "error": "Unsupported method"}
            
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_system_info(self) -> Dict:
        """システム情報を取得"""
        return {
            "trinity_supercharge": {
                "version": self.mana_os_integration['version'],
                "total_features": self.mana_os_integration['total_features'],
                "base_path": self.mana_os_integration['base_path'],
                "integrated_at": self.mana_os_integration['integrated_at']
            },
            "services": self.get_all_services_status(),
            "web_services": self.get_web_services(),
            "categories": self.get_categories(),
            "quick_actions": self.get_quick_actions()
        }

# グローバルインスタンス
_trinity_integration = None

def get_trinity_integration():
    """統合インスタンスを取得"""
    global _trinity_integration
    if _trinity_integration is None:
        _trinity_integration = TrinitySuperchargeIntegration()
    return _trinity_integration

# 便利関数
def trinity_execute(service_id: str, action: str, **kwargs) -> Dict:
    """Trinityサービスを実行（簡易インターフェース）"""
    integration = get_trinity_integration()
    return integration.execute_service_action(service_id, action, **kwargs)

def trinity_status(service_id: Optional[str] = None) -> Dict:
    """Trinityサービスのステータスを取得"""
    integration = get_trinity_integration()
    if service_id:
        return integration.get_service_status(service_id)
    else:
        return {"services": integration.get_all_services_status()}

def trinity_info() -> Dict:
    """Trinity Superchargeの情報を取得"""
    integration = get_trinity_integration()
    return integration.get_system_info()

def main():
    """テスト実行"""
    integration = TrinitySuperchargeIntegration()
    
    if "--info" in sys.argv:
        info = integration.get_system_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    elif "--status" in sys.argv:
        status = integration.get_all_services_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif "--web" in sys.argv:
        web_services = integration.get_web_services()
        print(json.dumps(web_services, indent=2, ensure_ascii=False))
    
    else:
        print("""
🚀 Trinity Supercharge Integration for ManaOS

使い方:
  python3 trinity_supercharge_integration.py --info      システム情報
  python3 trinity_supercharge_integration.py --status    サービスステータス
  python3 trinity_supercharge_integration.py --web       Webサービス一覧

Pythonからの使用:
  from trinity_supercharge_integration import trinity_execute, trinity_status
  
  # ノート作成
  trinity_execute('auto_notes', 'create', title='タイトル', content='内容')
  
  # バックアップ
  trinity_execute('smart_backup', 'create')
  
  # ステータス確認
  trinity_status('unified_dashboard')
        """)

if __name__ == "__main__":
    main()


