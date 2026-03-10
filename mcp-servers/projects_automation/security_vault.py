#!/usr/bin/env python3
"""
🔐 Mana Security Vault
APIキーとトークンを暗号化して安全に保管するシステム
"""
import os
import json
from cryptography.fernet import Fernet
from pathlib import Path

class SecurityVault:
    def __init__(self, vault_path='/root/.mana_vault'):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(mode=0o700, exist_ok=True)
        
        self.key_file = self.vault_path / 'vault.key'
        self.data_file = self.vault_path / 'vault.dat'
        
        # 暗号化キーの生成または読み込み
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)
            os.chmod(self.key_file, 0o600)
        
        self.cipher = Fernet(self.key)
    
    def save_credentials(self, credentials):
        """認証情報を暗号化して保存"""
        data = json.dumps(credentials).encode()
        encrypted = self.cipher.encrypt(data)
        
        with open(self.data_file, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.data_file, 0o600)
        
        print(f"✅ 認証情報を暗号化保存: {self.data_file}")
    
    def load_credentials(self):
        """認証情報を復号化して読み込み"""
        if not self.data_file.exists():
            return {}
        
        with open(self.data_file, 'rb') as f:
            encrypted = f.read()
        
        data = self.cipher.decrypt(encrypted)
        return json.loads(data.decode())
    
    def get(self, key, default=None):
        """特定のキーを取得"""
        creds = self.load_credentials()
        return creds.get(key, default)
    
    def set(self, key, value):
        """特定のキーを設定"""
        creds = self.load_credentials()
        creds[key] = value
        self.save_credentials(creds)
    
    def delete(self, key):
        """特定のキーを削除"""
        creds = self.load_credentials()
        if key in creds:
            del creds[key]
            self.save_credentials(creds)
            print(f"🗑️  削除: {key}")
    
    def list_keys(self):
        """保存されているキーの一覧"""
        creds = self.load_credentials()
        return list(creds.keys())


def migrate_environment_variables():
    """環境変数からVaultへ移行"""
    vault = SecurityVault()
    
    # 移行対象のキー
    sensitive_keys = [
        'CIVITAI_API_KEY',
        'BRAVE_API_KEY',
        'GITHUB_PERSONAL_ACCESS_TOKEN',
        'HF_TOKEN',
        'TELEGRAM_BOT_TOKEN',
        'SLACK_BOT_TOKEN'
    ]
    
    migrated = []
    for key in sensitive_keys:
        value = os.environ.get(key)
        if value:
            vault.set(key, value)
            migrated.append(key)
            print(f"✅ 移行完了: {key}")
    
    return migrated


if __name__ == '__main__':
    print("🔐 Mana Security Vault - セットアップ")
    print("=" * 50)
    
    # 既存の環境変数を移行
    migrated = migrate_environment_variables()
    
    print(f"\n✅ {len(migrated)}個のキーを暗号化保存しました")
    
    # 確認
    vault = SecurityVault()
    print("\n📋 保存されたキー:")
    for key in vault.list_keys():
        value = vault.get(key)
        masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'  # type: ignore[index]
        print(f"  - {key}: {masked}")
    
    print("\n🔒 使用方法:")
    print("  from security_vault import SecurityVault")
    print("  vault = SecurityVault()")
    print("  api_key = vault.get('CIVITAI_API_KEY')")

