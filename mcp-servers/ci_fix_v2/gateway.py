#!/usr/bin/env python3
"""
Moltbot ゲートウェイクライアント（1本ゲート）
まなOS → Moltbot gateway/daemon に Plan を送り、結果を回収・監査ログに書き出す。
Plan 署名（HMAC-SHA256）で改ざん・中間者を防ぐ。
"""

from __future__ import annotations

import hmac
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from moltbot_integration.schema import Plan, ExecuteResult, AuditRecord

# 署名ヘッダ名（Gateway はこのヘッダで検証する）
PLAN_SIGNATURE_HEADER = "X-Plan-Signature"


def sign_plan_body(plan_json_bytes: bytes, secret: str) -> str:
    """
    Plan 本文の HMAC-SHA256 署名を生成。
    Gateway は同じ secret で検証し、通った Plan だけ受理する。
    """
    return hmac.new(
        secret.encode("utf-8") if isinstance(secret, str) else secret,
        plan_json_bytes,
        hashlib.sha256,
    ).hexdigest()


class MoltbotGatewayClient:
    """
    まなOS → Moltbot の1本ゲート。
    Plan を POST し、実行結果を取得。監査ログはローカルに書き出し（Git でコミット想定）。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        audit_dir: Optional[Path] = None,
        timeout_seconds: int = 60,
        secret: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("MOLTBOT_GATEWAY_URL", "")).rstrip("/")
        self.audit_dir = audit_dir or Path(__file__).parent.parent / "moltbot_audit"
        self.timeout_seconds = timeout_seconds
        self.secret = (secret or os.getenv("MOLTBOT_GATEWAY_SECRET", "")).strip() or None

    def submit_plan(self, plan: Plan) -> Dict[str, Any]:
        """
        Plan を Moltbot ゲートに送信。
        MOLTBOT_GATEWAY_SECRET が設定されていれば X-Plan-Signature を付与（Gateway 側で検証想定）。
        """
        if not REQUESTS_AVAILABLE:
            return {"ok": False, "error": "requests not installed"}
        if not self.base_url:
            return {"ok": False, "error": "MOLTBOT_GATEWAY_URL not set"}

        url = f"{self.base_url}/moltbot/plan"
        payload = plan.to_dict()
        body_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-Plan-Id": plan.plan_id}
        if self.secret:
            headers[PLAN_SIGNATURE_HEADER] = sign_plan_body(body_bytes, self.secret)

        try:
            r = requests.post(  # type: ignore[possibly-unbound]
                url,
                data=body_bytes,
                timeout=self.timeout_seconds,
                headers=headers,
            )
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_result(self, plan_id: str) -> Dict[str, Any]:
        """実行結果を取得（ポーリング用）。"""
        if not REQUESTS_AVAILABLE or not self.base_url:
            return {"ok": False, "error": "not configured"}

        url = f"{self.base_url}/moltbot/plan/{plan_id}/result"
        try:
            r = requests.get(url, timeout=self.timeout_seconds)  # type: ignore[possibly-unbound]
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_plan(self, plan_id: str) -> Dict[str, Any]:
        """実行中の Plan をキャンセル。"""
        if not REQUESTS_AVAILABLE or not self.base_url:
            return {"ok": False, "error": "not configured"}

        url = f"{self.base_url}/moltbot/plan/{plan_id}/cancel"
        try:
            r = requests.post(url, timeout=self.timeout_seconds)  # type: ignore[possibly-unbound]
            r.raise_for_status()
            return {"ok": True, "data": r.json() if r.content else {}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def write_audit(self, record: AuditRecord) -> Path:
        """
        監査レコードを 3層構成で moltbot_audit/YYYY-MM-DD/{plan_id}/ に書き出し。
        plan.json / decision.json / execute.jsonl / result.json / artifacts/
        Git でコミットする想定。
        """
        date_part = record.recorded_at[:10] if record.recorded_at else "unknown"
        dir_path = self.audit_dir / date_part / record.plan_id
        dir_path.mkdir(parents=True, exist_ok=True)

        (dir_path / "plan.json").write_text(
            json.dumps(record.plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if record.decision is not None:
            (dir_path / "decision.json").write_text(
                json.dumps(record.decision, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        (dir_path / "execute.json").write_text(
            json.dumps(record.execute, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if record.execute_events:
            with open(dir_path / "execute.jsonl", "w", encoding="utf-8") as f:
                for ev in record.execute_events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        (dir_path / "result.json").write_text(
            json.dumps(record.result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if record.artifacts_dir:
            (dir_path / "artifacts").mkdir(exist_ok=True)
        (dir_path / "commit_message.txt").write_text(
            record.to_commit_message(),
            encoding="utf-8",
        )
        return dir_path
