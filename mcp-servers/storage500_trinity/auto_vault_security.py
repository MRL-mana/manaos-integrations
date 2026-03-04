#!/usr/bin/env python3
"""
Phase 8: 自動検出＆即Vault移動システム
- systemd/cron起動時に平文APIキーを自動検出
- 発見したら自動的に.mana_vaultへ移動
- Slack通知で即座に報告
"""

import os
import re
import shutil
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path
import logging

class AutoVaultSecurity:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.vault_dir.mkdir(exist_ok=True, mode=0o700)
        
        # ログ設定
        self.log_file = self.vault_dir / "security_audit.log"
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # APIキーパターン（拡張版）
        self.api_patterns = [
            # 一般的なAPIキー
            r'[A-Za-z0-9]{20,}',
            # Slack Bot Token
            r'xoxb-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{20,}',
            # OpenAI API Key
            r'sk-[A-Za-z0-9]{48,}',
            # Google API Key
            r'AIza[0-9A-Za-z\\-_]{35}',
            # GitHub Token
            r'ghp_[A-Za-z0-9]{36}',
            # Discord Token
            r'[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}',
            # Telegram Bot Token
            r'[0-9]{8,}:[A-Za-z0-9_-]{35}',
            # AWS Access Key
            r'AKIA[0-9A-Z]{16}',
            # その他の長いトークン
            r'[A-Za-z0-9+/]{40,}={0,2}'
        ]
        
        # 検索対象ディレクトリ（軽量化）
        self.search_paths = [
            "/etc/environment",
            "/etc/systemd/system/",
            "/etc/cron.d/"
        ]
        
        # 除外パターン
        self.exclude_patterns = [
            r'.*\.log$',
            r'.*\.tmp$',
            r'.*\.cache$',
            r'.*\.vault.*',
            r'.*\.git.*',
            r'.*node_modules.*',
            r'.*\.pyc$'
        ]

    def is_excluded_file(self, file_path):
        """除外ファイルかどうかチェック"""
        for pattern in self.exclude_patterns:
            if re.search(pattern, str(file_path)):
                return True
        return False

    def looks_like_api_key(self, text):
        """テキストがAPIキーらしいかチェック"""
        for pattern in self.api_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 長さと文字種でフィルタリング
                if len(match) >= 20 and not match.isdigit():
                    return True, match
        return False, None

    def scan_file(self, file_path):
        """ファイルをスキャンしてAPIキーを検索"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            is_api, key = self.looks_like_api_key(content)
            if is_api:
                return {
                    'file': str(file_path),
                    'key': key,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.warning(f"ファイル読み込みエラー {file_path}: {e}")
        return None

    def scan_directory(self, directory):
        """ディレクトリを再帰的にスキャン"""
        findings = []
        
        try:
            for root, dirs, files in os.walk(directory):
                # .vaultディレクトリはスキップ
                dirs[:] = [d for d in dirs if not d.startswith('.vault')]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if self.is_excluded_file(file_path):
                        continue
                        
                    result = self.scan_file(file_path)
                    if result:
                        findings.append(result)
                        
        except Exception as e:
            self.logger.error(f"ディレクトリスキャンエラー {directory}: {e}")
            
        return findings

    def move_to_vault(self, finding):
        """発見したAPIキーをVaultに移動"""
        try:
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            vault_file = self.vault_dir / f"detected_key_{timestamp}.txt"
            
            # ファイル内容をVaultに保存
            with open(vault_file, 'w') as f:
                f.write(f"# 自動検出されたAPIキー\n")
                f.write(f"# 検出時刻: {finding['timestamp']}\n")
                f.write(f"# 元ファイル: {finding['file']}\n")
                f.write(f"# 検出されたキー: {finding['key']}\n\n")
                f.write(finding['content'])
            
            # 元ファイルからAPIキーを削除
            self.remove_api_key_from_file(finding['file'], finding['key'])
            
            # パーミッション設定
            os.chmod(vault_file, 0o600)
            
            self.logger.info(f"APIキーをVaultに移動: {vault_file}")
            return vault_file
            
        except Exception as e:
            self.logger.error(f"Vault移動エラー: {e}")
            return None

    def remove_api_key_from_file(self, file_path, api_key):
        """元ファイルからAPIキーを削除"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # APIキーを含む行を削除
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                if api_key not in line:
                    new_lines.append(line)
                else:
                    # コメントアウト
                    new_lines.append(f"# SECURITY: APIキーをVaultに移動済み - {line}")
            
            with open(file_path, 'w') as f:
                f.write('\n'.join(new_lines))
                
            self.logger.info(f"元ファイルからAPIキーを削除: {file_path}")
            
        except Exception as e:
            self.logger.error(f"APIキー削除エラー {file_path}: {e}")

    def send_slack_notification(self, findings):
        """Slack通知を送信"""
        try:
            # Slack設定を読み込み
            slack_config = self.vault_dir / "slack_config.json"
            if not slack_config.exists():
                self.logger.warning("Slack設定ファイルが見つかりません")
                return
            
            with open(slack_config, 'r') as f:
                config = json.load(f)
            
            webhook_url = config.get('webhook_url')
            if not webhook_url:
                self.logger.warning("Slack webhook URLが設定されていません")
                return
            
            # 通知メッセージ作成
            message = {
                "text": f"🚨 セキュリティアラート: {len(findings)}件のAPIキーを検出",
                "attachments": []
            }
            
            for i, finding in enumerate(findings[:5]):  # 最大5件まで
                attachment = {
                    "color": "danger",
                    "title": f"検出 #{i+1}",
                    "fields": [
                        {"title": "ファイル", "value": finding['file'], "short": False},
                        {"title": "検出時刻", "value": finding['timestamp'], "short": True},
                        {"title": "キー", "value": f"`{finding['key'][:20]}...`", "short": True}
                    ]
                }
                message["attachments"].append(attachment)
            
            # Slack送信
            response = requests.post(webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                self.logger.info("Slack通知送信成功")
            else:
                self.logger.error(f"Slack通知送信失敗: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Slack通知エラー: {e}")

    def run_scan(self):
        """メインスキャン実行"""
        self.logger.info("=== Phase 8: 自動セキュリティスキャン開始 ===")
        
        all_findings = []
        
        # 各パスをスキャン
        for search_path in self.search_paths:
            if os.path.exists(search_path):
                if os.path.isfile(search_path):
                    result = self.scan_file(search_path)
                    if result:
                        all_findings.append(result)
                else:
                    findings = self.scan_directory(search_path)
                    all_findings.extend(findings)
        
        if all_findings:
            self.logger.warning(f"{len(all_findings)}件のAPIキーを検出")
            
            # 各発見をVaultに移動
            for finding in all_findings:
                vault_file = self.move_to_vault(finding)
                if vault_file:
                    finding['vault_file'] = str(vault_file)
            
            # Slack通知
            self.send_slack_notification(all_findings)
            
            # 結果をJSONで保存
            result_file = self.vault_dir / f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(all_findings, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"スキャン結果を保存: {result_file}")
        else:
            self.logger.info("APIキーは検出されませんでした")
        
        self.logger.info("=== 自動セキュリティスキャン完了 ===")
        return len(all_findings)

if __name__ == "__main__":
    scanner = AutoVaultSecurity()
    findings_count = scanner.run_scan()
    print(f"検出件数: {findings_count}")
