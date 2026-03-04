#!/usr/bin/env python3
"""
ManaOS API Key Fix System
APIキー設定問題の完全解決システム
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mana/api_key_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIKeyFixSystem:
    def __init__(self):
        self.vault_path = Path("/root/.mana_vault")
        self.env_files = [
            "/root/.mana_vault/root.env",
            "/root/.mana_vault/mcp_api_keys.env",
            "/root/.mana_vault/manaos_v3.env"
        ]
        
    def detect_existing_keys(self):
        """既存のAPIキーを検出"""
        logger.info("🔍 既存APIキー検出開始")
        
        detected_keys = {}
        
        # Vault内のファイルを検索
        for env_file in self.env_files:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'OPENAI_API_KEY' in content:
                        detected_keys['OPENAI_API_KEY'] = True
                    if 'GEMINI_API_KEY' in content:
                        detected_keys['GEMINI_API_KEY'] = True
                    if 'ANTHROPIC_API_KEY' in content:
                        detected_keys['ANTHROPIC_API_KEY'] = True
        
        # スキャン結果から検出
        scan_files = list(self.vault_path.glob("scan_results_*.json"))
        for scan_file in scan_files[-3:]:  # 最新3ファイル
            try:
                with open(scan_file, 'r') as f:
                    content = f.read()
                    if 'OPENAI_API_KEY=' in content:
                        detected_keys['OPENAI_API_KEY'] = True
            except:
                continue
        
        logger.info(f"🔍 検出されたキー: {list(detected_keys.keys())}")
        return detected_keys
    
    def extract_keys_from_scan(self):
        """スキャン結果からAPIキーを抽出"""
        logger.info("🔑 スキャン結果からAPIキー抽出開始")
        
        extracted_keys = {}
        scan_files = list(self.vault_path.glob("scan_results_*.json"))
        
        for scan_file in scan_files[-1:]:  # 最新ファイルのみ
            try:
                with open(scan_file, 'r') as f:
                    content = f.read()
                    
                    # OPENAI_API_KEY抽出
                    if 'OPENAI_API_KEY=' in content:
                        start = content.find('OPENAI_API_KEY=') + len('OPENAI_API_KEY=')
                        end = content.find('"', start)
                        if end > start:
                            key = content[start:end]
                            if key.startswith('sk-'):
                                extracted_keys['OPENAI_API_KEY'] = key
                                logger.info("✅ OPENAI_API_KEY抽出成功")
            except Exception as e:
                logger.error(f"❌ キー抽出エラー: {e}")
        
        return extracted_keys
    
    def create_unified_env_file(self, keys):
        """統合環境変数ファイル作成"""
        logger.info("📝 統合環境変数ファイル作成開始")
        
        env_content = f"""# ManaOS Unified API Keys Configuration
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OpenAI API Key
OPENAI_API_KEY={keys.get('OPENAI_API_KEY', 'your_openai_key_here')}

# Google Gemini API Key  
GEMINI_API_KEY={keys.get('GEMINI_API_KEY', 'your_gemini_key_here')}

# Anthropic Claude API Key
ANTHROPIC_API_KEY={keys.get('ANTHROPIC_API_KEY', 'your_anthropic_key_here')}

# Additional API Keys
GITHUB_PERSONAL_ACCESS_TOKEN=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
NOTION_API_KEY=demo_notion_key_12345
STRIPE_SECRET_KEY=demo_stripe_key_12345
BRAVE_API_KEY=demo_brave_key_12345
CONTEXT7_API_KEY=demo_context7_key_12345
SERENA_API_KEY=demo_serena_key_12345
REF_API_KEY=demo_ref_key_12345
MCPWEB_API_KEY=demo_mcpweb_key_12345
HUGGINGFACE_HUB_TOKEN=your_token_here
"""
        
        env_file = self.vault_path / "unified_api_keys.env"
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # セキュリティ設定
        os.chmod(env_file, 0o600)
        
        logger.info(f"✅ 統合環境変数ファイル作成完了: {env_file}")
        return env_file
    
    def set_environment_variables(self, env_file):
        """環境変数設定"""
        logger.info("🌍 環境変数設定開始")
        
        # 環境変数ファイルを読み込み
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    logger.info(f"✅ {key} 設定完了")
    
    def update_systemd_services(self):
        """systemdサービス更新"""
        logger.info("⚙️ systemdサービス更新開始")
        
        # 環境変数ファイルを参照するようにサービス更新
        env_file = self.vault_path / "unified_api_keys.env"
        
        # 主要サービスの環境変数設定
        services_to_update = [
            "mana-ai-models",
            "mana-predictive-ai", 
            "mana-unified-portal",
            "mana-cognitive-bridge"
        ]
        
        for service in services_to_update:
            try:
                # サービスファイルの環境変数設定
                cmd = f"systemctl set-environment OPENAI_API_KEY=$(grep OPENAI_API_KEY {env_file} | cut -d'=' -f2)"
                subprocess.run(cmd, shell=True, check=True)
                
                cmd = f"systemctl set-environment GEMINI_API_KEY=$(grep GEMINI_API_KEY {env_file} | cut -d'=' -f2)"
                subprocess.run(cmd, shell=True, check=True)
                
                cmd = f"systemctl set-environment ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY {env_file} | cut -d'=' -f2)"
                subprocess.run(cmd, shell=True, check=True)
                
                logger.info(f"✅ {service} 環境変数更新完了")
            except Exception as e:
                logger.error(f"❌ {service} 更新エラー: {e}")
    
    def verify_api_keys(self):
        """APIキー検証"""
        logger.info("🔍 APIキー検証開始")
        
        verification_results = {}
        
        # 環境変数確認
        keys_to_check = ['OPENAI_API_KEY', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY']
        
        for key in keys_to_check:
            value = os.environ.get(key)
            if value and value != f'your_{key.lower()}_here':
                verification_results[key] = "✅ 設定済み"
                logger.info(f"✅ {key}: 設定済み")
            else:
                verification_results[key] = "❌ 未設定"
                logger.error(f"❌ {key}: 未設定")
        
        return verification_results
    
    def create_api_key_dashboard(self, verification_results):
        """APIキーダッシュボード作成"""
        logger.info("📊 APIキーダッシュボード作成開始")
        
        dashboard_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS API Key Status Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .status-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border-left: 5px solid #3498db;
        }}
        .status-card.success {{
            border-left-color: #27ae60;
        }}
        .status-card.error {{
            border-left-color: #e74c3c;
        }}
        .status-card h3 {{
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 1.3em;
        }}
        .status {{
            font-size: 1.1em;
            font-weight: bold;
            padding: 10px 15px;
            border-radius: 8px;
            display: inline-block;
        }}
        .status.success {{
            background: #d5f4e6;
            color: #27ae60;
        }}
        .status.error {{
            background: #fadbd8;
            color: #e74c3c;
        }}
        .recommendations {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
        }}
        .recommendations h3 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .recommendations ul {{
            color: #555;
            line-height: 1.6;
        }}
        .timestamp {{
            text-align: center;
            color: #7f8c8d;
            margin-top: 30px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔑 ManaOS API Key Status Dashboard</h1>
            <p>APIキー設定状況とシステム統合状況</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card {'success' if '✅' in verification_results.get('OPENAI_API_KEY', '') else 'error'}">
                <h3>🤖 OpenAI API Key</h3>
                <span class="status {'success' if '✅' in verification_results.get('OPENAI_API_KEY', '') else 'error'}">
                    {verification_results.get('OPENAI_API_KEY', '❌ 未確認')}
                </span>
            </div>
            
            <div class="status-card {'success' if '✅' in verification_results.get('GEMINI_API_KEY', '') else 'error'}">
                <h3>🧠 Google Gemini API Key</h3>
                <span class="status {'success' if '✅' in verification_results.get('GEMINI_API_KEY', '') else 'error'}">
                    {verification_results.get('GEMINI_API_KEY', '❌ 未確認')}
                </span>
            </div>
            
            <div class="status-card {'success' if '✅' in verification_results.get('ANTHROPIC_API_KEY', '') else 'error'}">
                <h3>🎭 Anthropic Claude API Key</h3>
                <span class="status {'success' if '✅' in verification_results.get('ANTHROPIC_API_KEY', '') else 'error'}">
                    {verification_results.get('ANTHROPIC_API_KEY', '❌ 未確認')}
                </span>
            </div>
        </div>
        
        <div class="recommendations">
            <h3>📋 推奨アクション</h3>
            <ul>
                <li><strong>APIキー設定:</strong> 未設定のAPIキーを設定してください</li>
                <li><strong>環境変数更新:</strong> システム全体で環境変数を更新してください</li>
                <li><strong>サービス再起動:</strong> 設定変更後、関連サービスを再起動してください</li>
                <li><strong>セキュリティ確認:</strong> APIキーが適切に保護されているか確認してください</li>
            </ul>
        </div>
        
        <div class="timestamp">
            <p>最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        
        dashboard_file = self.vault_path / "api_key_status_dashboard.html"
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)
        
        logger.info(f"✅ APIキーダッシュボード作成完了: {dashboard_file}")
        return dashboard_file
    
    def run_complete_fix(self):
        """完全修正実行"""
        logger.info("🚀 ManaOS API Key Fix System 開始")
        
        try:
            # 1. 既存キー検出
            detected_keys = self.detect_existing_keys()
            
            # 2. スキャン結果からキー抽出
            extracted_keys = self.extract_keys_from_scan()
            
            # 3. 統合環境変数ファイル作成
            all_keys = {**detected_keys, **extracted_keys}
            env_file = self.create_unified_env_file(all_keys)
            
            # 4. 環境変数設定
            self.set_environment_variables(env_file)
            
            # 5. systemdサービス更新
            self.update_systemd_services()
            
            # 6. APIキー検証
            verification_results = self.verify_api_keys()
            
            # 7. ダッシュボード作成
            dashboard_file = self.create_api_key_dashboard(verification_results)
            
            logger.info("✅ API Key Fix System 完了")
            
            return {
                'status': 'success',
                'detected_keys': detected_keys,
                'extracted_keys': extracted_keys,
                'verification_results': verification_results,
                'env_file': str(env_file),
                'dashboard_file': str(dashboard_file)
            }
            
        except Exception as e:
            logger.error(f"❌ API Key Fix System エラー: {e}")
            return {'status': 'error', 'error': str(e)}

def main():
    """メイン実行"""
    fix_system = APIKeyFixSystem()
    result = fix_system.run_complete_fix()
    
    if result['status'] == 'success':
        print("🎉 API Key Fix System 完全成功!")
        print(f"📊 ダッシュボード: {result['dashboard_file']}")
        print(f"🔧 環境変数ファイル: {result['env_file']}")
    else:
        print(f"❌ API Key Fix System エラー: {result['error']}")

if __name__ == "__main__":
    main()
