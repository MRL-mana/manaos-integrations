#!/usr/bin/env python3
"""
🔐 Mana Security Vault v2.0
二重暗号化システム（Fernet + GPG）
"""
import os
import json
import gnupg
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import datetime
import hashlib
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityVaultV2:
    """二重暗号化Vaultシステム"""
    
    def __init__(self, vault_dir='/root/.mana_vault'):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(mode=0o700, exist_ok=True)
        
        self.master_key_file = self.vault_dir / 'master.key'
        self.gpg_key_file = self.vault_dir / 'gpg_master.asc'
        self.vault_file = self.vault_dir / 'vault_v2.dat'
        self.audit_log = self.vault_dir / 'audit.log'
        
        # GPG初期化
        self.gpg = gnupg.GPG(gnupghome=str(self.vault_dir / '.gnupg'))
        
        # Vault初期化
        self._initialize_vault()
    
    def _initialize_vault(self):
        """Vaultを初期化"""
        # マスターキーの生成または読み込み
        if not self.master_key_file.exists():
            logger.info("🔧 Generating new master key...")
            master_key = Fernet.generate_key()
            
            # GPG鍵が存在しない場合は生成
            if not self.gpg.list_keys():
                logger.info("🔧 Generating GPG key pair...")
                self._generate_gpg_key()
            
            # マスターキーをGPGで暗号化して保存
            encrypted_master = self._encrypt_with_gpg(master_key)
            with open(self.gpg_key_file, 'wb') as f:
                f.write(encrypted_master)
            
            # セキュリティのため、平文のマスターキーは一時メモリのみ
            self.fernet = Fernet(master_key)
            del master_key  # メモリから削除
            
            logger.info("✅ Master key generated and encrypted with GPG")
        else:
            # 既存のマスターキーを読み込み
            with open(self.gpg_key_file, 'rb') as f:
                encrypted_master = f.read()
            
            master_key = self._decrypt_with_gpg(encrypted_master)
            self.fernet = Fernet(master_key)
            del master_key
            logger.info("✅ Master key loaded from GPG-encrypted storage")
        
        # Vaultデータの読み込み
        if self.vault_file.exists():
            with open(self.vault_file, 'rb') as f:
                encrypted_data = f.read()
            
            try:
                decrypted_data = self.fernet.decrypt(encrypted_data)
                self.vault_data = json.loads(decrypted_data.decode())
            except IOError:
                logger.warning("⚠️ Failed to decrypt vault, creating new vault")
                self.vault_data = {}
        else:
            self.vault_data = {}
            logger.info("🆕 Creating new vault")
    
    def _generate_gpg_key(self):
        """GPG鍵ペアを生成"""
        key_params = self.gpg.gen_key_input(
            name_real='Mana Security Vault',
            name_email='mana@localhost',
            passphrase='',  # パスフレーズなし（システム認証に依存）
            key_type='RSA',
            key_length=4096,
            expire_date='10y'  # 10年間有効
        )
        
        key = self.gpg.gen_key(key_params)
        logger.info(f"✅ GPG key generated: {key}")
        
        # 公開鍵をエクスポート
        public_key = self.gpg.export_keys(str(key))
        with open(self.vault_dir / 'public.asc', 'w') as f:
            f.write(public_key)
        
        return str(key)
    
    def _encrypt_with_gpg(self, data):
        """GPGで暗号化"""
        keys = self.gpg.list_keys()
        if not keys:
            raise Exception("No GPG keys available")
        
        encrypted = self.gpg.encrypt(data, keys[0]['fingerprint'], always_trust=True)
        if not encrypted.ok:
            raise Exception(f"GPG encryption failed: {encrypted.status}")
        
        return str(encrypted).encode()
    
    def _decrypt_with_gpg(self, encrypted_data):
        """GPGで復号化"""
        decrypted = self.gpg.decrypt(encrypted_data)
        if not decrypted.ok:
            raise Exception(f"GPG decryption failed: {decrypted.status}")
        
        return bytes(str(decrypted), 'utf-8')
    
    def _save_vault(self):
        """Vaultを保存"""
        # JSON → Fernet暗号化
        json_data = json.dumps(self.vault_data, indent=2)
        encrypted_data = self.fernet.encrypt(json_data.encode())
        
        # ファイルに書き込み
        with open(self.vault_file, 'wb') as f:
            f.write(encrypted_data)
        
        os.chmod(self.vault_file, 0o600)
        logger.info("💾 Vault saved with double encryption")
    
    def _audit_log_access(self, action, key_name, success=True):
        """アクセス監査ログを記録"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'key_name': key_name,
            'success': success,
            'user': os.getenv('USER', 'unknown')
        }
        
        with open(self.audit_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def set(self, key_name, value, metadata=None):
        """キーと値を保存"""
        try:
            self.vault_data[key_name] = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'access_count': 0,
                'hash': hashlib.sha256(value.encode()).hexdigest()[:16]
            }
            
            self._save_vault()
            self._audit_log_access('SET', key_name, True)
            logger.info(f"✅ Key '{key_name}' saved to vault")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save key '{key_name}': {e}")
            self._audit_log_access('SET', key_name, False)
            return False
    
    def get(self, key_name):
        """キーの値を取得"""
        try:
            if key_name not in self.vault_data:
                logger.warning(f"⚠️ Key '{key_name}' not found in vault")
                self._audit_log_access('GET', key_name, False)
                return None
            
            # アクセスカウントを更新
            self.vault_data[key_name]['access_count'] += 1
            self.vault_data[key_name]['last_accessed'] = datetime.now().isoformat()
            self._save_vault()
            
            self._audit_log_access('GET', key_name, True)
            return self.vault_data[key_name]['value']
        except Exception as e:
            logger.error(f"❌ Failed to retrieve key '{key_name}': {e}")
            self._audit_log_access('GET', key_name, False)
            return None
    
    def delete(self, key_name):
        """キーを削除"""
        try:
            if key_name in self.vault_data:
                del self.vault_data[key_name]
                self._save_vault()
                self._audit_log_access('DELETE', key_name, True)
                logger.info(f"🗑️ Key '{key_name}' deleted from vault")
                return True
            else:
                logger.warning(f"⚠️ Key '{key_name}' not found")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to delete key '{key_name}': {e}")
            self._audit_log_access('DELETE', key_name, False)
            return False
    
    def list_keys(self):
        """Vault内のキー一覧を取得"""
        return list(self.vault_data.keys())
    
    def get_key_info(self, key_name):
        """キーの詳細情報を取得"""
        if key_name not in self.vault_data:
            return None
        
        info = self.vault_data[key_name].copy()
        info.pop('value', None)  # 値自体は返さない
        return info
    
    def rotate_master_key(self):
        """マスターキーをローテーション（90日ごと推奨）"""
        logger.info("🔄 Rotating master key...")
        
        # 既存データをすべて取得
        old_data = {k: v['value'] for k, v in self.vault_data.items()}
        
        # 新しいマスターキーを生成
        new_master_key = Fernet.generate_key()
        new_fernet = Fernet(new_master_key)
        
        # 新しいマスターキーをGPGで暗号化
        encrypted_master = self._encrypt_with_gpg(new_master_key)
        with open(self.gpg_key_file, 'wb') as f:
            f.write(encrypted_master)
        
        # 新しいFernetで再暗号化
        self.fernet = new_fernet
        del new_master_key
        
        # データを再保存
        for key, value in old_data.items():
            self.vault_data[key]['value'] = value
            self.vault_data[key]['updated_at'] = datetime.now().isoformat()
        
        self._save_vault()
        logger.info("✅ Master key rotation completed")
    
    def integrity_check(self):
        """整合性チェック"""
        issues = []
        
        # GPG鍵の存在確認
        if not self.gpg.list_keys():
            issues.append("GPG key not found")
        
        # マスターキーファイルの確認
        if not self.gpg_key_file.exists():
            issues.append("GPG-encrypted master key file not found")
        
        # Vaultファイルの確認
        if not self.vault_file.exists():
            issues.append("Vault data file not found")
        
        # ハッシュ検証
        for key_name, data in self.vault_data.items():
            if 'hash' in data and 'value' in data:
                current_hash = hashlib.sha256(data['value'].encode()).hexdigest()[:16]
                if current_hash != data['hash']:
                    issues.append(f"Hash mismatch for key '{key_name}'")
        
        if issues:
            logger.warning(f"⚠️ Integrity check found {len(issues)} issue(s)")
            return False, issues
        else:
            logger.info("✅ Integrity check passed")
            return True, []
    
    def export_backup(self, backup_path):
        """バックアップをエクスポート（GPG暗号化）"""
        try:
            backup_data = {
                'version': '2.0',
                'timestamp': datetime.now().isoformat(),
                'vault_data': self.vault_data
            }
            
            json_data = json.dumps(backup_data, indent=2)
            encrypted_backup = self._encrypt_with_gpg(json_data.encode())
            
            with open(backup_path, 'wb') as f:
                f.write(encrypted_backup)
            
            logger.info(f"✅ Backup exported to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Backup export failed: {e}")
            return False

# CLI機能
if __name__ == "__main__":
    import sys
    
    vault = SecurityVaultV2()
    
    if len(sys.argv) < 2:
        print("Usage: security_vault_v2.py [set|get|delete|list|info|integrity|rotate|backup]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'set' and len(sys.argv) >= 4:
        key_name = sys.argv[2]
        value = sys.argv[3]
        vault.set(key_name, value)
        print(f"✅ Key '{key_name}' saved")
    
    elif command == 'get' and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        value = vault.get(key_name)
        if value:
            print(value)
        else:
            print(f"❌ Key '{key_name}' not found")
    
    elif command == 'delete' and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        if vault.delete(key_name):
            print(f"✅ Key '{key_name}' deleted")
    
    elif command == 'list':
        keys = vault.list_keys()
        print(f"📋 Vault contains {len(keys)} keys:")
        for key in keys:
            print(f"  - {key}")
    
    elif command == 'info' and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        info = vault.get_key_info(key_name)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"❌ Key '{key_name}' not found")
    
    elif command == 'integrity':
        success, issues = vault.integrity_check()
        if success:
            print("✅ Integrity check passed")
        else:
            print("⚠️ Integrity issues found:")
            for issue in issues:
                print(f"  - {issue}")
    
    elif command == 'rotate':
        vault.rotate_master_key()
        print("✅ Master key rotated")
    
    elif command == 'backup' and len(sys.argv) >= 3:
        backup_path = sys.argv[2]
        if vault.export_backup(backup_path):
            print(f"✅ Backup saved to {backup_path}")
    
    else:
        print("❌ Invalid command or missing arguments")

