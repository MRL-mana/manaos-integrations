#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS × Obsidian × NotebookLM × Antigravity 統合スクリプト
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import httpx

try:
    from manaos_integrations._paths import ORCHESTRATOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import ORCHESTRATOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_service_logger("manaos-obsidian-integration")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ObsidianIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# Obsidian統合
try:
    from obsidian_integration import ObsidianIntegration
    OBSIDIAN_AVAILABLE = True
except ImportError:
    OBSIDIAN_AVAILABLE = False
    logger.warning("Obsidian統合モジュールが利用できません")

# 統一記憶システム
try:
    from memory_unified import UnifiedMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("統一記憶システムが利用できません")

# 設定
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "Obsidian Vault"))
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


class ObsidianNotebookLMAntigravityIntegration:
    """Obsidian × NotebookLM × Antigravity × ManaOS 統合クラス"""
    
    def __init__(self):
        """初期化"""
        self.vault_path = Path(OBSIDIAN_VAULT_PATH)
        
        # Obsidian統合
        if OBSIDIAN_AVAILABLE:
            self.obsidian = ObsidianIntegration(str(self.vault_path))
        else:
            self.obsidian = None
        
        # 統一記憶システム
        if MEMORY_AVAILABLE:
            self.memory = UnifiedMemory()
        else:
            self.memory = None
    
    def get_recent_daily_notes(self, days: int = 14) -> List[Path]:
        """直近N日のDailyノートを取得"""
        if not self.obsidian or not self.obsidian.is_available():
            logger.warning("Obsidianが利用できません")
            return []
        
        daily_dir = self.vault_path / "Daily"
        if not daily_dir.exists():
            logger.warning(f"Dailyディレクトリが見つかりません: {daily_dir}")
            return []
        
        notes = []
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            note_path = daily_dir / f"{date_str}.md"
            
            if note_path.exists():
                notes.append(note_path)
        
        logger.info(f"直近{days}日のDailyノート: {len(notes)}件")
        return notes
    
    def prepare_notebooklm_input(self, days: int = 14) -> Optional[Path]:
        """NotebookLM用の入力ファイルを準備"""
        notes = self.get_recent_daily_notes(days)
        
        if not notes:
            logger.warning("Dailyノートが見つかりません")
            return None
        
        # ノート内容を結合
        combined_content = f"# 週次分析用データ - {datetime.now().strftime('%Y-%m-%d')}\n\n## 期間: 直近{days}日\n\n"
        
        for note_path in notes:
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                note_name = note_path.stem
                combined_content += f"## {note_name}\n\n{content}\n\n---\n\n"
            except Exception as e:
                logger.error(f"ノート読み込みエラー: {note_path} - {e}")
                continue
        
        # Reviewディレクトリに保存
        review_dir = self.vault_path / "Review"
        review_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_file = review_dir / f"{date_str}-notebooklm-input.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(combined_content)
        
        logger.info(f"NotebookLM入力ファイル作成完了: {output_file}")
        return output_file
    
    def save_notebooklm_result(self, analysis_result: str, date_str: Optional[str] = None) -> Optional[Path]:
        """NotebookLMの分析結果を保存"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        review_dir = self.vault_path / "Review"
        review_dir.mkdir(parents=True, exist_ok=True)
        
        result_file = review_dir / f"{date_str}-notebooklm-result.md"
        
        content = f"""---
date: {date_str}
type: review
tags: [review, notebooklm, manaos]
source: notebooklm
---

# NotebookLM分析結果 - {date_str}

{analysis_result}

---
"""
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"NotebookLM結果保存完了: {result_file}")
        
        # ManaOSの記憶システムに登録
        if self.memory:
            try:
                memory_id = self.memory.store({
                    "content": analysis_result,
                    "metadata": {
                        "source": "notebooklm",
                        "date": date_str,
                        "tags": ["review", "notebooklm", "analysis"]
                    }
                }, format_type="research")
                logger.info(f"✅ 記憶システムに登録: {memory_id}")
            except Exception as e:
                logger.error(f"記憶システム登録エラー: {e}")
        
        return result_file
    
    def save_antigravity_result(self, content: str, title: str, output_type: str = "moc") -> Optional[Path]:
        """Antigravityの再構築結果を保存"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        if output_type == "moc":
            output_dir = self.vault_path / "MOCs"
            filename = f"{title}-MOC.md"
        elif output_type == "article":
            output_dir = self.vault_path / "Articles"
            filename = f"{date_str}-{title}.md"
        else:
            output_dir = self.vault_path / "Processed"
            filename = f"{date_str}-{title}.md"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Antigravity結果保存完了: {output_file}")
        
        # ManaOSの記憶システムに登録
        if self.memory:
            try:
                memory_id = self.memory.store({
                    "content": content,
                    "metadata": {
                        "source": "antigravity",
                        "type": output_type,
                        "title": title,
                        "tags": ["antigravity", output_type]
                    }
                }, format_type="research")
                logger.info(f"✅ 記憶システムに登録: {memory_id}")
            except Exception as e:
                logger.error(f"記憶システム登録エラー: {e}")
        
        return output_file
    
    def send_to_slack(self, message: str):
        """Slackに通知を送信"""
        if not SLACK_WEBHOOK_URL:
            logger.warning("Slack Webhook URLが設定されていません")
            return False
        
        try:
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.post(
                SLACK_WEBHOOK_URL,
                json={"text": message},
                timeout=timeout
            )
            
            if response.status_code == 200:
                logger.info("Slack通知送信成功")
                return True
            else:
                logger.error(f"Slack通知送信失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Slack", "method": "webhook"},
                user_message="Slackへの通知送信に失敗しました"
            )
            logger.error(f"Slack通知エラー: {error.message}")
            return False


def main():
    """メイン関数"""
    integration = ObsidianNotebookLMAntigravityIntegration()
    
    print("🔧 Obsidian × NotebookLM × Antigravity × ManaOS 統合テスト")
    print()
    
    # NotebookLM入力ファイルを準備
    print("📊 NotebookLM入力ファイルを準備中...")
    input_file = integration.prepare_notebooklm_input(days=14)
    
    if input_file:
        print(f"✅ 作成完了: {input_file}")
        print()
        print("次のステップ:")
        print("  1. NotebookLMを開く")
        print(f"  2. {input_file} を投入")
        print("  3. 質問テンプレート（notebooklm_question_templates.md）を使用")
        print("  4. 結果を integration.save_notebooklm_result() で保存")
    else:
        print("❌ 入力ファイルの作成に失敗しました")
    
    print()
    print("🎉 統合テスト完了")


if __name__ == "__main__":
    main()




















