#!/usr/bin/env python3
"""
ManaOS 共通ルールエンジン（セミ自動版）
全ツールで共有する修正ルールを管理
- rules_pending.yaml: 候補ルール（承認待ち）
- rules_active.yaml: 適用中ルール（承認済み）
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RuleEngine:
    """共通ルールエンジン（セミ自動版）"""

    def __init__(self, rules_dir: str = "/root/manaos_learning/rules"):
        self.rules_dir = Path(rules_dir)
        self.rules_dir.mkdir(exist_ok=True)

        # アクティブルール（適用中）
        self.active_rules_file = self.rules_dir / "rules_active.yaml"

        # ペンディングルール（承認待ち）
        self.pending_rules_file = self.rules_dir / "rules_pending.yaml"

        # 設定ファイル
        self.config_file = self.rules_dir / "rule_config.yaml"

        self.rules = self._load_rules()
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        if not self.config_file.exists():
            default_config = {
                "auto_apply_enabled": False,  # 完全自動適用はOFF
                "min_occurrences_for_pending": 3,  # 候補になる最小出現回数
                "min_occurrences_for_auto": 10,  # 自動承認の最小出現回数（未使用）
                "require_manual_approval": True,  # 手動承認必須
                "last_updated": datetime.now().isoformat()
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f, allow_unicode=True)
            return default_config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            return {}

    def _load_rules(self) -> Dict[str, Any]:
        """ルールファイルを読み込み（アクティブのみ）"""
        if not self.active_rules_file.exists():
            # デフォルトルールを作成
            self._create_default_rules()

        try:
            with open(self.active_rules_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"ルール読み込みエラー: {e}")
            return {}

    def _load_pending_rules(self) -> Dict[str, Any]:
        """ペンディングルールを読み込み"""
        if not self.pending_rules_file.exists():
            return {"rules": []}

        try:
            with open(self.pending_rules_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"rules": []}
        except Exception as e:
            logger.error(f"ペンディングルール読み込みエラー: {e}")
            return {"rules": []}

    def _create_default_rules(self):
        """デフォルトルールを作成"""
        default_rules = {
            "rules": [
                {
                    "id": "common_fullwidth_to_halfwidth",
                    "target": ["pdf_excel", "text_cleaner", "summary_bot"],
                    "pattern": "全角英数字",
                    "action": "半角へ変換",
                    "regex": None,
                    "replace": None,
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "common_amount_fix_semicolon",
                    "target": ["pdf_excel"],
                    "pattern": "数字の間に ;",
                    "action": "; を , に置換",
                    "regex": r"(?<=\d);\s*(?=\d)",
                    "replace": ",",
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "common_mixed_comma_semicolon",
                    "target": ["pdf_excel"],
                    "pattern": "; , または , ;",
                    "action": "カンマに統一",
                    "regex": r";\s*,\s*|,\s*;\s*",
                    "replace": ",",
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "common_fullwidth_space",
                    "target": ["pdf_excel", "text_cleaner", "summary_bot"],
                    "pattern": "全角スペース",
                    "action": "半角スペースに変換",
                    "regex": r"　",
                    "replace": " ",
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                }
            ]
        }

        with open(self.active_rules_file, "w", encoding="utf-8") as f:
            yaml.dump(default_rules, f, allow_unicode=True, default_flow_style=False)

        logger.info("デフォルトルールを作成しました")

    def get_rules_for_tool(self, tool: str, include_pending: bool = False) -> List[Dict[str, Any]]:
        """
        特定ツール用のルールを取得

        Args:
            tool: ツール名
            include_pending: Trueの場合はペンディングルールも含める

        Returns:
            適用可能なルールのリスト
        """
        all_rules = self.rules.get("rules", [])
        applicable = []

        for rule in all_rules:
            targets = rule.get("target", [])
            if tool in targets or "all" in targets:
                applicable.append(rule)

        # ペンディングルールも含める場合
        if include_pending:
            pending = self._load_pending_rules()
            for rule in pending.get("rules", []):
                targets = rule.get("target", [])
                if tool in targets or "all" in targets:
                    applicable.append({**rule, "status": "pending"})

        return applicable

    def apply_rules(self, text: str, tool: str, learning_enabled: bool = True) -> str:
        """
        ルールを適用してテキストを修正

        Args:
            text: 修正対象のテキスト
            tool: ツール名
            learning_enabled: 学習レイヤーが有効かどうか

        Returns:
            修正後のテキスト
        """
        if not text or not learning_enabled:
            return text

        rules = self.get_rules_for_tool(tool, include_pending=False)  # アクティブのみ
        result = text

        for rule in rules:
            rule_id = rule.get("id")
            regex = rule.get("regex")
            replace = rule.get("replace")
            replace_func = rule.get("replace_func")

            if regex and replace:
                try:
                    result = re.sub(regex, replace, result)
                except Exception as e:
                    logger.warning(f"ルール適用エラー ({rule_id}): {e}")

            elif replace_func:
                # 関数ベースの置換（例: 日付変換）
                if replace_func == "convert_reiwa_date":
                    result = self._convert_reiwa_date(result)

        return result

    def _convert_reiwa_date(self, text: str) -> str:
        """令和日付を西暦に変換（R7.11.24 → 2025-11-24）"""
        def replace_date(match):
            reiwa_year = int(match.group(1))
            month = match.group(2)
            day = match.group(3)
            # 令和年を西暦に変換（令和元年=2019年）
            seireki_year = 2018 + reiwa_year
            return f"{seireki_year}-{month}-{day}"

        return re.sub(r"R(\d+)\.(\d+)\.(\d+)", replace_date, text)

    def add_rule_to_pending(
        self,
        rule_id: str,
        target: List[str],
        pattern: str,
        action: str,
        occurrences: int,
        regex: Optional[str] = None,
        replace: Optional[str] = None,
        replace_func: Optional[str] = None,
        source: str = "auto_extracted"
    ) -> bool:
        """
        新しいルールをペンディング（候補箱）に追加

        Args:
            rule_id: ルールID
            target: 適用対象ツールのリスト
            pattern: パターン説明
            action: アクション説明
            occurrences: 出現回数（信頼度指標）
            regex: 正規表現パターン
            replace: 置換文字列
            replace_func: 置換関数名
            source: ルールの出所（"auto_extracted", "manual"など）

        Returns:
            追加成功したかどうか
        """
        pending = self._load_pending_rules()

        if "rules" not in pending:
            pending["rules"] = []

        # 既存ルールをチェック
        for rule in pending["rules"]:
            if rule.get("id") == rule_id:
                # 既にある場合は出現回数を更新
                rule["occurrences"] = max(rule.get("occurrences", 0), occurrences)
                rule["last_seen"] = datetime.now().isoformat()
                with open(self.pending_rules_file, "w", encoding="utf-8") as f:
                    yaml.dump(pending, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"ペンディングルールを更新しました: {rule_id} (出現回数: {occurrences})")
                return True

        # 新規追加
        new_rule = {
            "id": rule_id,
            "target": target,
            "pattern": pattern,
            "action": action,
            "regex": regex,
            "replace": replace,
            "replace_func": replace_func,
            "status": "pending",
            "occurrences": occurrences,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }

        pending["rules"].append(new_rule)

        with open(self.pending_rules_file, "w", encoding="utf-8") as f:
            yaml.dump(pending, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"ペンディングルールを追加しました: {rule_id} (出現回数: {occurrences})")
        return True

    def approve_pending_rule(self, rule_id: str) -> bool:
        """
        ペンディングルールを承認してアクティブに昇格

        Args:
            rule_id: ルールID

        Returns:
            承認成功したかどうか
        """
        pending = self._load_pending_rules()
        rule_to_approve = None

        # ペンディングから削除
        for i, rule in enumerate(pending.get("rules", [])):
            if rule.get("id") == rule_id:
                rule_to_approve = pending["rules"].pop(i)
                break

        if not rule_to_approve:
            logger.warning(f"ペンディングルールが見つかりません: {rule_id}")
            return False

        # アクティブに追加
        if "rules" not in self.rules:
            self.rules["rules"] = []

        # 既存チェック
        for i, rule in enumerate(self.rules["rules"]):
            if rule.get("id") == rule_id:
                # 更新
                self.rules["rules"][i] = {
                    **rule_to_approve,
                    "status": "active",
                    "approved_at": datetime.now().isoformat()
                }
                break
        else:
            # 新規追加
            self.rules["rules"].append({
                **rule_to_approve,
                "status": "active",
                "approved_at": datetime.now().isoformat()
            })

        # 保存
        with open(self.pending_rules_file, "w", encoding="utf-8") as f:
            yaml.dump(pending, f, allow_unicode=True, default_flow_style=False)

        with open(self.active_rules_file, "w", encoding="utf-8") as f:
            yaml.dump(self.rules, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"ルールを承認しました: {rule_id}")
        return True

    def reject_pending_rule(self, rule_id: str) -> bool:
        """
        ペンディングルールを却下

        Args:
            rule_id: ルールID

        Returns:
            却下成功したかどうか
        """
        pending = self._load_pending_rules()

        for i, rule in enumerate(pending.get("rules", [])):
            if rule.get("id") == rule_id:
                pending["rules"].pop(i)
                with open(self.pending_rules_file, "w", encoding="utf-8") as f:
                    yaml.dump(pending, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"ペンディングルールを却下しました: {rule_id}")
                return True

        logger.warning(f"ペンディングルールが見つかりません: {rule_id}")
        return False

    def get_pending_rules(self) -> List[Dict[str, Any]]:
        """ペンディングルール一覧を取得"""
        pending = self._load_pending_rules()
        return pending.get("rules", [])

    def get_active_rules(self) -> List[Dict[str, Any]]:
        """アクティブルール一覧を取得"""
        return self.rules.get("rules", [])

    def disable_rule(self, rule_id: str) -> bool:
        """
        アクティブルールを無効化

        Args:
            rule_id: ルールID

        Returns:
            無効化成功したかどうか
        """
        for rule in self.rules.get("rules", []):
            if rule.get("id") == rule_id:
                rule["status"] = "disabled"
                rule["disabled_at"] = datetime.now().isoformat()
                with open(self.active_rules_file, "w", encoding="utf-8") as f:
                    yaml.dump(self.rules, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"ルールを無効化しました: {rule_id}")
                return True

        return False

    def enable_rule(self, rule_id: str) -> bool:
        """
        無効化されたルールを再有効化

        Args:
            rule_id: ルールID

        Returns:
            再有効化成功したかどうか
        """
        for rule in self.rules.get("rules", []):
            if rule.get("id") == rule_id:
                rule["status"] = "active"
                if "disabled_at" in rule:
                    del rule["disabled_at"]
                with open(self.active_rules_file, "w", encoding="utf-8") as f:
                    yaml.dump(self.rules, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"ルールを再有効化しました: {rule_id}")
                return True

        return False


# === グローバルインスタンス ===
_global_engine = None

def get_rule_engine() -> RuleEngine:
    """グローバルなRuleEngineインスタンスを取得"""
    global _global_engine
    if _global_engine is None:
        _global_engine = RuleEngine()
    return _global_engine
