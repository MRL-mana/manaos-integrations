#!/usr/bin/env python3
"""
セキュア設定ローダー
Vaultから機密情報を安全に読み込む
"""

import os
from pathlib import Path
from typing import Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureConfigLoader:
    """セキュア設定ローダー"""
    
    def __init__(self, vault_dir: str = "/root/.vault"):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(mode=0o700, exist_ok=True)
        
    def load_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        機密情報を読み込む
        
        Args:
            key: 秘密情報のキー名
            default: デフォルト値
            
        Returns:
            秘密情報の値、見つからない場合はdefault
        """
        # 1. 環境変数から読み込み（最優先）
        env_value = os.getenv(key)
        if env_value:
            logger.info(f"✅ 環境変数から読み込み: {key}")
            return env_value
        
        # 2. Vaultから読み込み
        vault_file = self.vault_dir / f"{key.lower()}.txt"
        if vault_file.exists():
            try:
                with open(vault_file, 'r') as f:
                    value = f.read().strip()
                logger.info(f"✅ Vaultから読み込み: {key}")
                return value
            except Exception as e:
                logger.error(f"Vault読み込みエラー: {e}")
        
        # 3. デフォルト値
        if default:
            logger.warning(f"⚠️ デフォルト値を使用: {key}")
            return default
        
        logger.error(f"❌ 秘密情報が見つかりません: {key}")
        return None
    
    def save_secret(self, key: str, value: str):
        """
        機密情報を保存
        
        Args:
            key: 秘密情報のキー名
            value: 保存する値
        """
        vault_file = self.vault_dir / f"{key.lower()}.txt"
        
        try:
            with open(vault_file, 'w') as f:
                f.write(value)
            
            # ファイル権限を600に設定
            os.chmod(vault_file, 0o600)
            
            logger.info(f"✅ 秘密情報を保存: {key}")
        except Exception as e:
            logger.error(f"秘密情報保存エラー: {e}")
    
    def load_config(self) -> Dict[str, str]:
        """
        全設定を読み込む
        
        Returns:
            設定の辞書
        """
        config = {}
        
        # 必要な秘密情報のキーリスト
        secrets = [
            "SLACK_BOT_TOKEN",
            "OPENAI_API_KEY",
            "AWS_ACCESS_KEY",
            "GOOGLE_API_KEY"
        ]
        
        for key in secrets:
            value = self.load_secret(key)
            if value:
                config[key] = value
        
        return config


def main():
    """メイン実行"""
    loader = SecureConfigLoader()
    
    print("=" * 60)
    print("🔒 セキュア設定ローダー")
    print("=" * 60)
    
    # 設定を読み込み
    print("\n📊 設定読み込み中...")
    config = loader.load_config()
    
    if config:
        print("\n✅ 読み込み成功:")
        for key in config.keys():
            print(f"  ✓ {key}")
    else:
        print("\n⚠️ 設定が見つかりません")
    
    print("\n💡 使用方法:")
    print("  from secure_config_loader import SecureConfigLoader")
    print("  loader = SecureConfigLoader()")
    print("  token = loader.load_secret('SLACK_BOT_TOKEN')")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

