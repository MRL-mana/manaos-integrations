from ai_simulator.safety_framework.monitoring.metrics_exporter import heartbeat
try:
    from ai_simulator.api.approval_api import app as approval_app
    from ai_simulator.api.evolution_api import router as evolution_router
    from ai_simulator.api.reflexive_api import router as reflexive_router
    from ai_simulator.api.vision_api import router as vision_router

    # Evolution APIを統合
    approval_app.include_router(evolution_router)
    # Reflexive Mode APIを統合
    approval_app.include_router(reflexive_router)
    # Vision Mode APIを統合
    approval_app.include_router(vision_router)
except ImportError:
    # フォールバック: 最小限のFastAPIアプリ
    from fastapi import FastAPI
    approval_app = FastAPI(title="AI Simulator API")
from ai_simulator.ai_core.training_loop import main as run_training
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse
import os
import threading
import time
import uvicorn

# Prometheus metrics endpointをFastAPIアプリに統合
@approval_app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ダッシュボードUI
from fastapi.responses import FileResponse

dashboard_path = "/root/ai_simulator/src/ai_simulator/api/static/dashboard.html"

@approval_app.get("/")
async def dashboard():
    """ダッシュボードUI"""
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not found"}

@approval_app.get("/dashboard")
async def dashboard_alt():
    """ダッシュボードUI（別パス）"""
    return await dashboard()

if __name__ == "__main__":
    # 環境変数でトレーニング実行を制御
    run_training_flag = os.getenv("AISIM_RUN_TRAINING", "false").lower() == "true"

    if run_training_flag:
        # トレーニングループをバックグラウンドで実行
        def training_thread():
            while True:
                run_training()
                time.sleep(60)  # 1分待機して再実行

        t = threading.Thread(target=training_thread, daemon=True)
        t.start()

    # メトリクスハートビートを定期更新（バックグラウンド）
    def heartbeat_thread():
        while True:
            heartbeat()
            time.sleep(30)  # 30秒ごとにハートビート更新

    hb_thread = threading.Thread(target=heartbeat_thread, daemon=True)
    hb_thread.start()

    # FastAPIアプリ起動（Prometheus metrics統合済み）
    uvicorn.run(approval_app, host="0.0.0.0", port=9108, log_level="info")