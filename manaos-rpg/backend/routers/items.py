from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import REG, REPO_ROOT
from core.helpers import load_yaml
from collectors.items_collector import resolve_item_roots, safe_resolve_under_root, scan_items

router = APIRouter()


@router.get("/api/items")
def api_items(limit: int = 120) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    items_yaml = load_yaml(REG / "items.yaml")
    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    items_recent = scan_items(item_roots)
    return {
        "roots": [{"id": r.id, "label": r.label} for r in item_roots],
        "recent": items_recent[:limit],
    }


@router.get("/files/{root_id}/{rel_path:path}")
def get_item_file(root_id: str, rel_path: str):
    items_yaml = load_yaml(REG / "items.yaml")
    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    root = next((r for r in item_roots if r.id == root_id), None)
    if root is None:
        raise HTTPException(status_code=404, detail="unknown root_id")

    p = safe_resolve_under_root(root.path, rel_path)
    if p is None or (not p.exists()) or (not p.is_file()):
        raise HTTPException(status_code=404, detail="file not found")

    return FileResponse(path=str(p))
