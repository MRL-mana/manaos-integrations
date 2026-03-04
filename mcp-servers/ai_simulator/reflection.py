"""
Reflection Writer: 学びをテンプレ化し「MCT（成功手順の道具）」化
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SKILLS_REGISTRY_FILE = Path("/root/ai_simulator/knowledge/skills_registry.json")
IMPROVEMENTS_LOG_FILE = Path("/root/ai_simulator/IMPROVEMENTS_COMPLETE.md")

def _ensure_knowledge_dir():
    """知識ディレクトリ確保"""
    SKILLS_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_skills_registry() -> Dict[str, Any]:
    """スキルレジストリを読み込む"""
    _ensure_knowledge_dir()
    if SKILLS_REGISTRY_FILE.exists():
        try:
            with open(SKILLS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load skills registry: {e}")
    return {
        "mcts": [],
        "blocked": []
    }

def save_skills_registry(registry: Dict[str, Any]):
    """スキルレジストリを保存"""
    _ensure_knowledge_dir()
    try:
        with open(SKILLS_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save skills registry: {e}")

def register_successful_variant(
    variant_id: str,
    task: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    reward: float,
    min_reward_threshold: float = 0.85
) -> bool:
    """
    成功バリアントをMCTとして登録
    :param variant_id: バリアントID
    :param task: タスク名
    :param params: パラメータ
    :param metrics: メトリクス
    :param reward: リワード
    :param min_reward_threshold: 登録最小リワード
    :return: 登録成功ならTrue
    """
    if reward < min_reward_threshold:
        logger.debug(f"Variant {variant_id} reward {reward:.3f} < threshold {min_reward_threshold}, skipping MCT registration")
        return False
    
    registry = load_skills_registry()
    
    # 既存MCTかチェック
    existing_mct = None
    for mct in registry["mcts"]:
        if mct.get("id") == variant_id:
            existing_mct = mct
            break
    
    # MCT登録
    mct_entry = {
        "id": variant_id,
        "applicable_to": [task],
        "params": params,
        "proven": True,
        "registered_at": datetime.now().isoformat(),
        "metrics": {
            "reward": reward,
            "success_rate": metrics.get("success_rate", 0.0),
            "p95_ms": metrics.get("p95_ms", 0),
            "error_rate": metrics.get("error_rate", 0.0),
        },
        "notes": f"p95 {metrics.get('p95_ms', 0)}ms, success {metrics.get('success_rate', 0.0):.1%}, reward {reward:.3f}"
    }
    
    if existing_mct:
        # 更新
        existing_mct.update(mct_entry)
        logger.info(f"Updated MCT: {variant_id}")
    else:
        # 新規追加
        registry["mcts"].append(mct_entry)
        logger.info(f"Registered new MCT: {variant_id}")
    
    save_skills_registry(registry)
    return True

def register_blocked_variant(
    variant_id: str,
    task: str,
    reason: str,
    failure_details: Optional[Dict[str, Any]] = None
):
    """
    失敗バリアントを禁止リストに登録
    :param variant_id: バリアントID
    :param task: タスク名
    :param reason: 失敗理由
    :param failure_details: 失敗詳細
    """
    registry = load_skills_registry()
    
    blocked_entry = {
        "id": variant_id,
        "task": task,
        "reason": reason,
        "blocked_at": datetime.now().isoformat(),
        "details": failure_details or {}
    }
    
    # 既存の禁止エントリかチェック
    existing_blocked = None
    for blocked in registry["blocked"]:
        if blocked.get("id") == variant_id:
            existing_blocked = blocked
            break
    
    if existing_blocked:
        # 更新
        existing_blocked.update(blocked_entry)
        logger.info(f"Updated blocked variant: {variant_id}")
    else:
        # 新規追加
        registry["blocked"].append(blocked_entry)
        logger.info(f"Blocked variant: {variant_id} - {reason}")
    
    save_skills_registry(registry)

def append_improvement_log(
    variant_id: str,
    task: str,
    delta_reward: float,
    delta_p95: float,
    adoption_reason: str
):
    """
    IMPROVEMENTS_COMPLETE.md に進化ログを追記
    :param variant_id: バリアントID
    :param task: タスク名
    :param delta_reward: リワード差分
    :param delta_p95: p95差分（ms）
    :param adoption_reason: 採択理由
    """
    try:
        _ensure_knowledge_dir()
        log_entry = f"""
## 進化ログ: {variant_id} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

- **タスク**: {task}
- **Δリワード**: {delta_reward:+.3f}
- **Δp95**: {delta_p95:+.0f}ms
- **採択理由**: {adoption_reason}
- **ステータス**: 採用

---
"""
        with open(IMPROVEMENTS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        logger.info(f"Appended improvement log for {variant_id}")
    except Exception as e:
        logger.error(f"Failed to append improvement log: {e}")
