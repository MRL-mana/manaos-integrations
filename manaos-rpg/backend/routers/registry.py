from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from core.config import REG
from core.helpers import load_yaml

router = APIRouter()


@router.get("/api/registry")
def api_registry() -> dict[str, Any]:
    return {
        "services": load_yaml(REG / "services.yaml").get("services") or [],
        "models": load_yaml(REG / "models.yaml").get("models") or [],
        "menu": load_yaml(REG / "features.yaml").get("menu") or [],
        "devices": load_yaml(REG / "devices.yaml").get("devices") or [],
        "quests": load_yaml(REG / "quests.yaml").get("quests") or [],
        "skills": load_yaml(REG / "skills.yaml").get("skills") or [],
        "items": load_yaml(REG / "items.yaml").get("items") or [],
        "prompts": load_yaml(REG / "prompts.yaml").get("prompts") or {},
        "actions": load_yaml(REG / "actions.yaml").get("actions") or [],
        "unified_proxy": load_yaml(REG / "unified_proxy.yaml").get("rules") or [],
    }
