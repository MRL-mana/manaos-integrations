#!/usr/bin/env python3
"""
監査ログシステム: ログ収集 + AI自己監査
"""
import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ログ設定
log_dir = Path("/root/logs/audit_system")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "audit_logger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Audit Log System",
    version="1.0.0",
    description="監査ログ + AI自己監査"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 設定 =====
class Config:
    """設定"""
    PORT = int(os.getenv("AUDIT_SYSTEM_PORT", "5021"))
    LOG_FILE = log_dir / "audit_chain.jsonl"
    AI_AUDIT_API_URL = os.getenv("AI_AUDIT_API_URL", "http://localhost:5015")
    CHAIN_HASH_ALGORITHM = "sha256"


# ===== データモデル =====
class AuditLog(BaseModel):
    """監査ログ"""
    timestamp: str
    service: str
    action: str
    user: Optional[str] = None
    request_id: Optional[str] = None
    details: Dict = {}
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None


# ===== ログチェーン管理 =====
class AuditLogChain:
    """監査ログチェーン（ハッシュ連鎖）"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.chain: List[AuditLog] = []
        self.last_hash: Optional[str] = None
        self.load_chain()

    def load_chain(self):
        """チェーンを読み込み"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            log_data = json.loads(line)
                            self.chain.append(AuditLog(**log_data))
                            self.last_hash = log_data.get("current_hash")
                logger.info(f"✅ チェーン読み込み完了: {len(self.chain)}件")
            except Exception as e:
                logger.error(f"チェーン読み込みエラー: {e}")

    def add_log(self, log: AuditLog) -> str:
        """ログを追加"""
        # 前のハッシュを設定
        log.previous_hash = self.last_hash

        # 現在のハッシュを計算
        log_data = {
            "timestamp": log.timestamp,
            "service": log.service,
            "action": log.action,
            "user": log.user,
            "request_id": log.request_id,
            "details": log.details,
            "previous_hash": log.previous_hash
        }
        log.current_hash = self._calculate_hash(log_data)

        # チェーンに追加
        self.chain.append(log)
        self.last_hash = log.current_hash

        # ファイルに追記
        self._append_to_file(log)

        logger.info(f"✅ ログ追加: {log.service} - {log.action}")
        return log.current_hash

    def _calculate_hash(self, data: Dict) -> str:
        """ハッシュを計算"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def _append_to_file(self, log: AuditLog):
        """ファイルに追記"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log.dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"ファイル追記エラー: {e}")

    def verify_chain(self) -> Dict:
        """チェーンの整合性を検証"""
        errors = []
        for i, log in enumerate(self.chain):
            if i > 0:
                prev_log = self.chain[i - 1]
                if log.previous_hash != prev_log.current_hash:
                    errors.append({
                        "index": i,
                        "expected": prev_log.current_hash,
                        "actual": log.previous_hash
                    })

        return {
            "valid": len(errors) == 0,
            "total_logs": len(self.chain),
            "errors": errors
        }


audit_chain = AuditLogChain(Config.LOG_FILE)


# ===== AI自己監査 =====
async def ai_audit_analysis(logs: List[AuditLog]) -> Dict:
    """AI自己監査分析"""
    try:
        # 最近のログを分析
        recent_logs = logs[-100:] if len(logs) > 100 else logs

        # ログを要約
        summary = {
            "total_actions": len(recent_logs),
            "services": {},
            "users": {},
            "actions": {}
        }

        for log in recent_logs:
            # サービス別集計
            service = log.service
            summary["services"][service] = summary["services"].get(service, 0) + 1

            # ユーザー別集計
            user = log.user or "anonymous"
            summary["users"][user] = summary["users"].get(user, 0) + 1

            # アクション別集計
            action = log.action
            summary["actions"][action] = summary["actions"].get(action, 0) + 1

        # AI分析（Trinity API経由）
        analysis_prompt = f"""
以下の監査ログを分析してください：
- 総アクション数: {summary['total_actions']}
- サービス別: {summary['services']}
- ユーザー別: {summary['users']}
- アクション別: {summary['actions']}

異常なパターンやセキュリティリスクがあれば指摘してください。
"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.AI_AUDIT_API_URL}/task",
                json={
                    "description": analysis_prompt,
                    "use_langgraph": False
                },
                timeout=30.0
            )
            response.raise_for_status()
            ai_response = response.json()

        return {
            "summary": summary,
            "ai_analysis": ai_response.get("result", "分析完了"),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"AI監査分析エラー: {e}")
        return {
            "summary": {},
            "ai_analysis": f"分析エラー: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "Audit Log System",
        "version": "1.0.0",
        "description": "監査ログ + AI自己監査",
        "endpoints": {
            "/log": "ログ追加",
            "/logs": "ログ一覧",
            "/verify": "チェーン検証",
            "/audit": "AI自己監査"
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    chain_status = audit_chain.verify_chain()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "total_logs": len(audit_chain.chain),
        "chain_valid": chain_status["valid"],
        "last_hash": audit_chain.last_hash,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/log")
async def add_log(request: Request):
    """ログを追加"""
    try:
        body = await request.json()

        log = AuditLog(
            timestamp=datetime.now().isoformat(),
            service=body.get("service", "unknown"),
            action=body.get("action", "unknown"),
            user=body.get("user"),
            request_id=body.get("request_id"),
            details=body.get("details", {})
        )

        hash_value = audit_chain.add_log(log)

        return {
            "success": True,
            "hash": hash_value,
            "log": log.dict()
        }

    except Exception as e:
        logger.error(f"ログ追加エラー: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/logs")
async def get_logs(limit: int = 100, offset: int = 0):
    """ログ一覧を取得"""
    logs = audit_chain.chain[-limit-offset:-offset if offset > 0 else None]
    return {
        "total": len(audit_chain.chain),
        "limit": limit,
        "offset": offset,
        "logs": [log.dict() for log in logs]
    }


@app.get("/verify")
async def verify_chain():
    """チェーンの整合性を検証"""
    status = audit_chain.verify_chain()
    return status


@app.get("/audit")
async def audit_analysis():
    """AI自己監査分析"""
    analysis = await ai_audit_analysis(audit_chain.chain)
    return analysis


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Audit Log System 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info(f"📁 ログファイル: {Config.LOG_FILE}")
    logger.info(f"✅ チェーン読み込み完了: {len(audit_chain.chain)}件")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Audit Log System シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

