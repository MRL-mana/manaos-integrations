#!/usr/bin/env python3
"""
このは側 Moltbot Gateway 最小実装（貼って動く）
POST /moltbot/plan で署名検証 → Plan保存 → executor.run(plan) → Result保存。
EXECUTOR=mock|moltbot で切替。数字（200/401/429）が揃ったら本物 Moltbot を executor に差し替える。
"""

import json
import os
import time
import hmac
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request

from moltbot_gateway.executor import run as executor_run

# データ保存先（このはでは /var/lib/moltbot_gateway、ローカルでは ./moltbot_gateway_data）
DATA_DIR = Path(os.getenv("MOLTBOT_GATEWAY_DATA_DIR", "moltbot_gateway_data"))
SECRET = (os.getenv("MOLTBOT_GATEWAY_SECRET", "") or "").strip()

DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "plans").mkdir(exist_ok=True)
(DATA_DIR / "results").mkdir(exist_ok=True)
(DATA_DIR / "status").mkdir(exist_ok=True)

app = FastAPI(title="Moltbot Gateway (minimal)")


def _verify_signature(plan_bytes: bytes, sig: Optional[str]) -> None:
    """SECRET 設定時のみ検証。未設定ならスキップ（ローカル試行用）。"""
    if not SECRET:
        return
    if not sig:
        raise HTTPException(status_code=401, detail="Missing X-Plan-Signature")
    mac = hmac.new(SECRET.encode("utf-8"), plan_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _set_status(plan_id: str, status: str) -> None:
    _write_json(
        DATA_DIR / "status" / f"{plan_id}.json",
        {"plan_id": plan_id, "status": status, "ts": time.time()},
    )


def _get_status(plan_id: str) -> Dict[str, Any]:
    return _read_json(DATA_DIR / "status" / f"{plan_id}.json")


def _validate_plan_constraints(plan: Dict[str, Any]) -> None:
    """
    事故らない守り3点：まなOSがバグっても外で止める。
    - write_paths 未指定 → 400（Phase1でも必須）
    - allowed_domains 未指定 → 400（web系scopeのみ。Phase1 file_organize は対象外）
    - max_actions 未指定 → 400（phase1_safe で入るので runner は落ちない）
    """
    constraints = plan.get("constraints") or {}
    scope = plan.get("scope") or {}
    allowed = scope.get("allowed_actions") or []
    # Phase1 file_organize は browser 系を含まない
    is_web_scope = any(
        a in ("browser_navigate", "browser_submit", "browser_purchase") for a in allowed
    )

    if not constraints.get("write_paths"):
        raise HTTPException(
            status_code=400,
            detail="constraints.write_paths required (Phase1 safety)",
        )
    if constraints.get("max_actions") is None:
        raise HTTPException(
            status_code=400,
            detail="constraints.max_actions required (phase1_safe sets 50)",
        )
    if is_web_scope and not constraints.get("allowed_domains"):
        raise HTTPException(
            status_code=400,
            detail="constraints.allowed_domains required for web scope",
        )


@app.post("/moltbot/plan")
async def submit_plan(request: Request, x_plan_signature: Optional[str] = Header(default=None)):
    """
    まなOS側は plan.to_dict() をそのまま body で送る（ラップなし）。
    署名検証 → Plan保存 → モック実行 → Result保存。
    """
    body_bytes = await request.body()
    _verify_signature(body_bytes, x_plan_signature)

    plan = json.loads(body_bytes.decode("utf-8"))
    plan_id = plan.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id required")

    _validate_plan_constraints(plan)

    # idempotency（超簡易）
    constraints = plan.get("constraints") or {}
    idem = constraints.get("idempotency_key")
    if idem:
        idem_path = DATA_DIR / "plans" / f"idempotency_{idem}.json"
        if idem_path.exists():
            existing = _read_json(idem_path)
            return {"ok": True, "plan_id": existing.get("plan_id", plan_id), "idempotent": True}
        _write_json(idem_path, {"plan_id": plan_id})

    _write_json(DATA_DIR / "plans" / f"{plan_id}.json", plan)
    _set_status(plan_id, "queued")

    # --- 実行バックエンド（EXECUTOR=mock|moltbot で切替） ---
    _set_status(plan_id, "running")
    result, execute_events = executor_run(plan)
    if "execute_events" not in result:
        result["execute_events"] = execute_events
    _write_json(DATA_DIR / "results" / f"{plan_id}.json", result)
    _set_status(plan_id, "completed")

    return {"ok": True, "plan_id": plan_id}


@app.get("/moltbot/plan/{plan_id}/result")
def get_result(plan_id: str):
    """実行結果を返す。まなOS側の client.get_result(plan_id) の data にそのまま渡る。"""
    result_path = DATA_DIR / "results" / f"{plan_id}.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="result not found")
    return _read_json(result_path)


@app.post("/moltbot/plan/{plan_id}/cancel")
def cancel(plan_id: str):
    try:
        st = _get_status(plan_id)
    except HTTPException:
        raise
    if st.get("status") in ("completed", "failed", "cancelled"):
        return {"ok": True, "status": st}
    _set_status(plan_id, "cancelled")
    return {"ok": True, "status": _get_status(plan_id)}


@app.get("/moltbot/health")
def health():
    return {"ok": True, "service": "moltbot_gateway"}
