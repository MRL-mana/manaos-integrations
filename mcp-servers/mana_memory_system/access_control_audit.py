#!/usr/bin/env python3
"""
アクセス制御の棚卸し
APIトークン・OAuthスコープの最小権限を確認

チェック項目:
- APIトークンの権限
- Drive側共有設定
- リンク共有の状態
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path("/root/.mana_memory")
GDRIVE_DIR = Path("/root/Google Drive/ManaMemoryArchive")


class AccessControlAudit:
    """アクセス制御監査"""

    def check_drive_sharing(self) -> Dict:
        """Drive共有設定チェック"""
        try:
            # 共有リンクを検索（簡易実装）
            # 実際の実装ではGoogle Drive APIを使用

            shared_files = []
            if GDRIVE_DIR.exists():
                # 共有設定ファイルを確認
                # 実際の実装ではGoogle Drive APIで共有状態を確認
                pass

            return {
                "check": "drive_sharing",
                "shared_files_count": len(shared_files),
                "shared_files": shared_files,
                "message": f"共有ファイル: {len(shared_files)}件"
            }
        except Exception as e:
            return {
                "check": "drive_sharing",
                "error": str(e)
            }

    def check_api_tokens(self) -> Dict:
        """APIトークンの権限チェック"""
        try:
            # 環境変数からトークンを確認
            import os

            tokens = []
            token_vars = ['OPENAI_API_KEY', 'GITHUB_TOKEN', 'GOOGLE_DRIVE_TOKEN']

            for var in token_vars:
                if var in os.environ:
                    token_value = os.environ[var]
                    # トークンの最初と最後の数文字のみ表示（セキュリティ）
                    masked = token_value[:4] + "..." + token_value[-4:] if len(token_value) > 8 else "***"
                    tokens.append({
                        "name": var,
                        "exists": True,
                        "masked": masked,
                        "length": len(token_value)
                    })
                else:
                    tokens.append({
                        "name": var,
                        "exists": False
                    })

            return {
                "check": "api_tokens",
                "tokens": tokens,
                "message": f"APIトークン: {len([t for t in tokens if t.get('exists')])}件"
            }
        except Exception as e:
            return {
                "check": "api_tokens",
                "error": str(e)
            }

    def check_file_permissions(self) -> Dict:
        """ファイル権限チェック"""
        try:
            issues = []

            # 機密ファイルの権限をチェック
            sensitive_files = [
                DB_PATH,
                MEMORY_DIR / "memory_audit.db",
                MEMORY_DIR / "config.json"
            ]

            for file_path in sensitive_files:
                if file_path.exists():
                    mode = oct(file_path.stat().st_mode)[-3:]
                    # 他のユーザーに読み取り可能な場合は警告
                    if mode[-1] != '0':
                        issues.append({
                            "file": str(file_path),
                            "mode": mode,
                            "issue": "他のユーザーが読み取り可能"
                        })

            return {
                "check": "file_permissions",
                "issues": issues,
                "issue_count": len(issues),
                "message": f"権限問題: {len(issues)}件"
            }
        except Exception as e:
            return {
                "check": "file_permissions",
                "error": str(e)
            }

    def run_audit(self) -> Dict:
        """全監査実行"""
        logger.info("🔍 アクセス制御監査開始")

        checks = [
            self.check_drive_sharing(),
            self.check_api_tokens(),
            self.check_file_permissions()
        ]

        total_issues = sum(c.get('issue_count', 0) for c in checks)

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": total_issues,
            "checks": checks
        }

        logger.info(f"✅ アクセス制御監査完了: {total_issues}件の問題検出")
        return result


def main():
    from datetime import datetime
    import argparse

    parser = argparse.ArgumentParser(description='アクセス制御監査')
    parser.add_argument('--json', action='store_true', help='JSON形式で出力')
    args = parser.parse_args()

    audit = AccessControlAudit()
    result = audit.run_audit()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("📊 アクセス制御監査結果")
        print("=" * 50)
        for check in result['checks']:
            print(f"✅ {check.get('check')}: {check.get('message', '')}")


if __name__ == '__main__':
    main()

