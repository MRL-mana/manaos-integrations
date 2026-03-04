#!/usr/bin/env python3
"""Trinity達をManaOSに統合"""
import json
from datetime import datetime

REGISTRY_FILE = "/root/manaos_systems_registry.json"

# Trinity達のリスト
TRINITY_SYSTEMS = {
    "trinity_conversation_api": {
        "name": "Trinity Conversation API",
        "port": 8083,
        "category": "ai",
        "description": "Trinity達との会話API"
    },
    "trinity_analytics_dashboard": {
        "name": "Trinity Analytics Dashboard",
        "port": 5011,
        "category": "dashboard",
        "description": "分析ダッシュボード"
    },
    "trinity_unified_dashboard": {
        "name": "Trinity Unified Dashboard",
        "port": 5009,
        "category": "dashboard",
        "description": "統合ダッシュボード"
    },
    "trinity_secure_api": {
        "name": "Trinity Secure API",
        "port": 5010,
        "category": "integration",
        "description": "認証API"
    },
    "trinity_ai_monitoring": {
        "name": "Trinity AI Monitoring",
        "port": 9001,
        "category": "monitoring",
        "description": "AI監視システム"
    },
    "trinity_remote_desktop": {
        "name": "Trinity Remote Desktop",
        "port": 8096,
        "category": "remote",
        "description": "リモートデスクトップ"
    },
    "trinity_google_services": {
        "name": "Trinity Google Services",
        "port": 8097,
        "category": "integration",
        "description": "Google連携"
    },
    "trinity_file_uploader": {
        "name": "Trinity File Uploader",
        "port": 8098,
        "category": "files",
        "description": "ファイルアップロード"
    }
}

print("🎭 Trinity達をManaOSに統合中...")
print("")

# レジストリ読み込みまたは作成
try:
    with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
        registry = json.load(f)
except FileNotFoundError:
    registry = {
        'systems': {},
        'trinity_systems': {},
        'last_updated': ''
    }

if 'trinity_systems' not in registry:
    registry['trinity_systems'] = {}

# Trinity達を登録
count = 0
for system_id, info in TRINITY_SYSTEMS.items():
    count += 1
    print(f"[{count}/{len(TRINITY_SYSTEMS)}] {info['name']}")
    
    registry['trinity_systems'][system_id] = {
        'name': info['name'],
        'description': info['description'],
        'category': info['category'],
        'port': info['port'],
        'health_check_url': f"http://localhost:{info['port']}/api/status",
        'registered_at': datetime.now().isoformat(),
        'status': 'active',
        'type': 'trinity',
        'priority': 'high',
        'auto_start': True
    }
    
    # systemsにも追加
    registry['systems'][system_id] = registry['trinity_systems'][system_id]

registry['last_updated'] = datetime.now().isoformat()
registry['total_systems'] = len(registry['systems'])

# 保存
with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print("")
print("✅ Trinity達の統合完了！")
print(f"📊 登録されたTrinity: {len(TRINITY_SYSTEMS)} 個")
print(f"📝 レジストリ: {REGISTRY_FILE}")
print("🌐 ダッシュボード: http://localhost:9999")
print("")
print("💖 もうTrinity達は孤立しません！")

