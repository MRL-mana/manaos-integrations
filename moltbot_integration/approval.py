#!/usr/bin/env python3
"""
Moltbot 統合：承認必須アクションの判定
人間の最終承認を挟むポイントを一元管理
"""

from moltbot_integration.schema import RiskLevel

# 承認必須のアクション（まなOSが Plan に載せず「承認依頼」だけ出す）
REQUIRES_APPROVAL_ACTIONS = frozenset(
    {
        # 外部送信
        "email_send",
        "slack_send",
        "dm_send",
        "post_publish",
        # 支払い・購入
        "payment",
        "cart_checkout",
        "browser_purchase",
        # 破壊操作
        "file_delete",
        "file_overwrite_bulk",
        "os_command",
        # 認証・秘密
        "password_input",
        "api_key_read",
        "credential_access",
    }
)


def action_requires_approval(action: str) -> bool:
    """指定アクションが承認必須か"""
    return action.strip().lower() in REQUIRES_APPROVAL_ACTIONS


def risk_requires_approval(risk_level: RiskLevel) -> bool:
    """risk_level が high なら原則承認必須"""
    return risk_level == RiskLevel.HIGH


def plan_requires_approval(
    risk_level: RiskLevel,
    steps: list,
) -> bool:
    """Plan 全体が承認必須か（risk=high または steps に承認必須アクションを含む）"""
    if risk_requires_approval(risk_level):
        return True
    for s in steps:
        act = getattr(s, "action", s.get("action") if isinstance(s, dict) else None)
        if act and action_requires_approval(act):
            return True
    return False
