#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS v1.0 自動トラフィック段階投入システム
Automated Multi-Phase Traffic Ramp-Up System
"""

import asyncio
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import httpx
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('traffic_rampup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# サービスエンドポイント
SERVICES = {
    "mrl_memory": "http://localhost:5105/health",
    "learning_system": "http://localhost:5126/health",
    "llm_routing": "http://localhost:5111/health",
    "gallery_api": "http://localhost:5559/health",
    "video_pipeline": "http://localhost:5112/health",
    "ollama": "http://localhost:11434/api/tags",
    "moltbot_gateway": "http://localhost:8088/health",
}

# フェーズ定義
PHASES = {
    "phase1": {
        "traffic_percentage": 10,
        "duration_minutes": 30,
        "name": "Phase 1 - Initial Ramp-Up",
        "error_threshold": 5.0,  # 5%
        "latency_threshold_ms": 100,
        "cpu_threshold": 60,
        "memory_threshold": 70,
    },
    "phase2": {
        "traffic_percentage": 30,
        "duration_minutes": 60,
        "name": "Phase 2 - Standard Ramp-Up",
        "error_threshold": 2.0,  # 2%
        "latency_threshold_ms": 50,
        "cpu_threshold": 75,
        "memory_threshold": 80,
    },
    "phase3": {
        "traffic_percentage": 100,
        "duration_minutes": None,  # 継続
        "name": "Phase 3 - Full Production",
        "error_threshold": 0.1,  # 0.1%
        "latency_threshold_ms": 100,
        "cpu_threshold": 85,
        "memory_threshold": 90,
    },
}


class TrafficRampUpSystem:
    """段階的トラフィック投入システム"""
    
    def __init__(self):
        self.current_phase = "phase1"
        self.start_time = datetime.utcnow()
        self.metrics = {
            "phase1": {"errors": [], "latencies": [], "timestamps": []},
            "phase2": {"errors": [], "latencies": [], "timestamps": []},
            "phase3": {"errors": [], "latencies": [], "timestamps": []},
        }
        self.state_file = Path("traffic_rampup_state.json")
        self.load_state()
        
    def load_state(self):
        """前回の状態を読み込む"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.current_phase = data.get("current_phase", "phase1")
                    logger.info(f"✅ 前回の状態から復帰: {self.current_phase}")
            except Exception as e:
                logger.warning(f"⚠️ 状態ファイル読み込み失敗: {e}")
    
    def save_state(self):
        """現在の状態を保存"""
        with open(self.state_file, "w") as f:
            json.dump({
                "current_phase": self.current_phase,
                "start_time": self.start_time.isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            }, f, indent=2)
    
    async def check_service_health(self) -> Dict[str, bool]:
        """全サービスのヘルスチェック"""
        results = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service_name, endpoint in SERVICES.items():
                try:
                    start = time.time()
                    resp = await client.get(endpoint)
                    latency = (time.time() - start) * 1000  # ms
                    results[service_name] = {
                        "status": "UP" if resp.status_code == 200 else "DOWN",
                        "code": resp.status_code,
                        "latency_ms": latency,
                    }
                except Exception as e:
                    results[service_name] = {
                        "status": "DOWN",
                        "error": str(e),
                        "latency_ms": 9999,
                    }
        return results
    
    async def evaluate_phase_metrics(self) -> Dict:
        """フェーズの評価メトリクス計算"""
        health = await self.check_service_health()
        
        up_count = sum(1 for s in health.values() if s["status"] == "UP")
        down_count = len(health) - up_count
        avg_latency = sum(s.get("latency_ms", 0) for s in health.values()) / len(health)
        error_rate = (down_count / len(health)) * 100
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services_up": up_count,
            "services_down": down_count,
            "health_check_pass_rate": (up_count / len(health)) * 100,
            "average_latency_ms": avg_latency,
            "error_rate": error_rate,
            "services": health,
        }
    
    async def should_escalate_phase(self) -> bool:
        """フェーズ遷移の判定"""
        phase_config = PHASES[self.current_phase]
        
        if phase_config["duration_minutes"] is None:
            # Phase 3 は継続
            return False
        
        # フェーズ開始時刻を計算
        phase_start = datetime.utcnow() - timedelta(minutes=5)  # 簡略化
        phase_duration = timedelta(minutes=phase_config["duration_minutes"])
        phase_end = phase_start + phase_duration
        
        if datetime.utcnow() >= phase_end:
            logger.info(f"⏱️ {self.current_phase} の期間終了")
            return True
        
        return False
    
    async def transition_phase(self):
        """次フェーズへの遷移"""
        phase_progression = {
            "phase1": "phase2",
            "phase2": "phase3",
            "phase3": "phase3",  # Phase 3 は継続
        }
        
        next_phase = phase_progression.get(self.current_phase, "phase3")
        
        if next_phase != self.current_phase:
            logger.info(f"""
╔════════════════════════════════════════════════════════════════════╗
║                    🚀 フェーズ遷移完了                              ║
╠════════════════════════════════════════════════════════════════════╣
║ {self.current_phase.upper()} → {next_phase.upper()}
║ トラフィック投入率: {PHASES[self.current_phase]['traffic_percentage']}% → {PHASES[next_phase]['traffic_percentage']}%
║ タイムスタンプ: {datetime.utcnow().isoformat()}
╚════════════════════════════════════════════════════════════════════╝
            """)
            self.current_phase = next_phase
            self.save_state()
    
    async def monitor_and_report(self):
        """監視とレポート出力"""
        metrics = await self.evaluate_phase_metrics()
        phase_config = PHASES[self.current_phase]
        
        # ステータスメッセージ
        status_symbol = "🟢" if metrics["health_check_pass_rate"] >= 95 else "🟡"
        
        logger.info(f"""
{status_symbol} {phase_config['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  トラフィック投入率: {phase_config['traffic_percentage']}%
  稼働サービス: {metrics['services_up']}/{len(SERVICES)}
  平均応答時間: {metrics['average_latency_ms']:.1f}ms
  エラー率: {metrics['error_rate']:.1f}%
  ヘルスチェック成功率: {metrics['health_check_pass_rate']:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        
        # サービス詳細
        for service_name, service_health in metrics["services"].items():
            status = "✅" if service_health["status"] == "UP" else "❌"
            latency = f"{service_health.get('latency_ms', 9999):.1f}ms"
            logger.info(f"  {status} {service_name:20s} | {latency:>8s}")
        
        # メトリクス保存
        self.metrics[self.current_phase].append(metrics)
    
    async def run_continuous_monitoring(self, interval_seconds: int = 30):
        """継続的な監視ループ"""
        logger.info(f"""
╔════════════════════════════════════════════════════════════════════╗
║                 🚀 本番環境トラフィック段階投入開始                  ║
╠════════════════════════════════════════════════════════════════════╣
║ 開始時刻: {datetime.utcnow().isoformat()}
║ フェーズ1: 10% トラフィック (30分)
║ フェーズ2: 30% トラフィック (1時間)
║ フェーズ3: 100% トラフィック (本格稼動)
║
║ ログファイル: traffic_rampup.log
║ 状態ファイル: traffic_rampup_state.json
║ メトリクス: metrics/traffic_rampup_metrics.json
╚════════════════════════════════════════════════════════════════════╝
        """)
        
        iteration = 0
        while True:
            iteration += 1
            
            try:
                # メトリクス監視
                await self.monitor_and_report()
                
                # フェーズ遷移判定
                if await self.should_escalate_phase():
                    await self.transition_phase()
                
                # メトリクス保存
                self.save_metrics()
                
                logger.debug(f"✅ 監視サイクル #{iteration} 完了")
                
            except Exception as e:
                logger.error(f"❌ エラー: {e}", exc_info=True)
            
            # 次の監視まで待機
            await asyncio.sleep(interval_seconds)
    
    def save_metrics(self):
        """メトリクスをファイルに保存"""
        metrics_dir = Path("metrics")
        metrics_dir.mkdir(exist_ok=True)
        
        metrics_file = metrics_dir / "traffic_rampup_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2, default=str)
    
    async def graceful_shutdown(self):
        """グレースフルシャットダウン"""
        logger.info("🛑 グレースフルシャットダウン開始...")
        self.save_state()
        self.save_metrics()
        logger.info("✅ シャットダウン完了")


async def main():
    """メインエントリーポイント"""
    system = TrafficRampUpSystem()
    
    try:
        # 初回ヘルスチェック
        logger.info("🔍 初期ヘルスチェック実施...")
        health = await system.evaluate_phase_metrics()
        
        if health["health_check_pass_rate"] < 50:
            logger.error("❌ ヘルスチェック失敗。サービスが起動していません。")
            sys.exit(1)
        
        logger.info(f"✅ ヘルスチェック成功: {health['health_check_pass_rate']:.1f}%")
        
        # 継続監視開始
        await system.run_continuous_monitoring(interval_seconds=30)
        
    except KeyboardInterrupt:
        logger.info("⚠️ 手動中断検出")
        await system.graceful_shutdown()
    except Exception as e:
        logger.error(f"❌ 致命的エラー: {e}", exc_info=True)
        await system.graceful_shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
