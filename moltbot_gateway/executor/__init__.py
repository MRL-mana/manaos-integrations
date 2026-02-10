# Gateway 実行バックエンド（EXECUTOR=mock|moltbot で切替）
# 数字（200/401/429）が揃ったら A 完了 → 本物 Moltbot 接続をここに差し替える

import os
from typing import Any, Dict, List, Tuple

EXECUTOR = (os.getenv("EXECUTOR", "mock") or "mock").strip().lower()


def get_executor():
    """EXECUTOR 環境変数に応じて mock または moltbot を返す。"""
    if EXECUTOR == "moltbot":
        from moltbot_gateway.executor.moltbot import MoltbotExecutor

        return MoltbotExecutor()
    from moltbot_gateway.executor import mock

    return mock.MockExecutor()


def run(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    実行バックエンドに Plan を渡し、(result_dict, execute_events) を返す。
    gateway_app はここだけ呼べばよい。
    """
    return get_executor().run(plan)
