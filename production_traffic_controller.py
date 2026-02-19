#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Production Traffic Controller
本番環境トラフィック投入自動管理システム
段階的トラフィック投入とヘルスチェック統合
"""

import json
import time
import requests
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
import os

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# 本番環境エンドポイント
PRODUCTION_ENDPOINTS = {
    'mrl_memory': 'http://localhost:5105/health',
    'learning_system': 'http://localhost:5126/health',
    'llm_routing': 'http://localhost:5111/health',
    'gallery_api': 'http://localhost:5559/health',
    'video_pipeline': 'http://localhost:5112/health',
    'ollama': 'http://localhost:11434/api/tags',
    'moltbot_gateway': 'http://localhost:8088/health',
}

# トラフィック投入フェーズ定義
TRAFFIC_PHASES = [
    {
        'phase': 1,
        'traffic_percent': 10,
        'duration_minutes': 30,
        'description': '初期段階: 10% トラフィック投入',
        'max_error_rate': 0.05,  # 5%
        'max_latency_ms': 100,
        'health_check_interval': 10,  # 10秒ごと
    },
    {
        'phase': 2,
        'traffic_percent': 30,
        'duration_minutes': 60,
        'description': '増加段階: 30% トラフィック投入',
        'max_error_rate': 0.02,  # 2%
        'max_latency_ms': 50,
        'health_check_interval': 15,
    },
    {
        'phase': 3,
        'traffic_percent': 100,
        'duration_minutes': 0,  # 継続
        'description': '本格稼動: 100% トラフィック投入',
        'max_error_rate': 0.001,  # 0.1%
        'max_latency_ms': 100,
        'health_check_interval': 30,
    },
]


class HealthCheckResult:
    """ヘルスチェック結果クラス"""
    
    def __init__(self):
        self.healthy_services: int = 0
        self.total_services: int = len(PRODUCTION_ENDPOINTS)
        self.avg_latency: float = 0.0
        self.error_services: List[str] = []
        self.timestamp = datetime.now()
        self.response_times: Dict[str, float] = {}
        
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'healthy_count': self.healthy_services,
            'total_count': self.total_services,
            'avg_latency_ms': round(self.avg_latency, 2),
            'error_services': self.error_services,
            'response_times': self.response_times,
            'health_percent': round((self.healthy_services / self.total_services) * 100, 1),
        }


class ProductionTrafficController:
    """本番環境トラフィック管理コントローラー"""
    
    def __init__(self):
        self.current_phase = 1
        self.start_time = datetime.now()
        self.phase_start_time = datetime.now()
        self.traffic_history: List[Dict] = []
        self.health_check_history: List[Dict] = []
        self.error_count = 0
        self.request_count = 0
        self.monitoring_active = True
        self.phase_metrics = {
            1: {'errors': 0, 'requests': 0},
            2: {'errors': 0, 'requests': 0},
            3: {'errors': 0, 'requests': 0},
        }
        
    def check_service_health(self) -> HealthCheckResult:
        """全サービスのヘルスチェック実行"""
        result = HealthCheckResult()
        response_times = []
        
        for service_name, endpoint in PRODUCTION_ENDPOINTS.items():
            try:
                start = time.time()
                response = requests.get(endpoint, timeout=5)
                elapsed = (time.time() - start) * 1000  # ミリ秒
                
                result.response_times[service_name] = round(elapsed, 2)
                response_times.append(elapsed)
                
                if response.status_code == 200:
                    result.healthy_services += 1
                else:
                    result.error_services.append(f"{service_name} (HTTP {response.status_code})")
                    
            except requests.exceptions.RequestException as e:
                result.error_services.append(f"{service_name} (timeout/error)")
                
        if response_times:
            result.avg_latency = sum(response_times) / len(response_times)
        else:
            result.avg_latency = 0.0
            
        return result
    
    def get_current_phase_config(self) -> Dict:
        """現在のフェーズ設定を取得"""
        for phase_config in TRAFFIC_PHASES:
            if phase_config['phase'] == self.current_phase:
                return phase_config
        return TRAFFIC_PHASES[-1]  # デフォルトはフェーズ3
    
    def should_advance_phase(self) -> bool:
        """次フェーズへの移行判定"""
        phase_config = self.get_current_phase_config()
        
        # フェーズ3は継続（duration_minutes = 0）
        if self.current_phase == 3:
            return False
        
        # 指定時間経過をチェック
        elapsed = datetime.now() - self.phase_start_time
        duration = timedelta(minutes=phase_config['duration_minutes'])
        
        if elapsed < duration:
            return False
        
        # 直近のメトリクスをチェック
        if not self.health_check_history:
            return True
        
        # 直近5分間のメトリクスで健全性を確認
        recent_checks = [
            h for h in self.health_check_history 
            if datetime.fromisoformat(h['timestamp']) > datetime.now() - timedelta(minutes=5)
        ]
        
        if not recent_checks:
            return True
        
        avg_health = sum(h['health_percent'] for h in recent_checks) / len(recent_checks)
        
        # 健全性が90%以上なら次フェーズへ
        return avg_health >= 90
    
    def advance_phase(self) -> bool:
        """次フェーズへ移行"""
        if self.current_phase >= 3:
            logger.info("すべてのフェーズが完了。本格稼動中...")
            return False
        
        self.current_phase += 1
        self.phase_start_time = datetime.now()
        self.phase_metrics[self.current_phase] = {'errors': 0, 'requests': 0}
        
        phase_config = self.get_current_phase_config()
        logger.warning(f"")
        logger.warning(f"╔═══════════════════════════════════════╗")
        logger.warning(f"║  フェーズ {self.current_phase} への移行")
        logger.warning(f"║  {phase_config['description']}")
        logger.warning(f"║  {phase_config['traffic_percent']}% トラフィック投入")
        logger.warning(f"╚═══════════════════════════════════════╝")
        logger.warning(f"")
        
        return True
    
    def simulate_traffic(self, num_requests: int = 100):
        """トラフィック投入シミュレーション"""
        phase_config = self.get_current_phase_config()
        
        for i in range(num_requests):
            try:
                # ランダムにエンドポイントを選択
                import random
                endpoint = random.choice(list(PRODUCTION_ENDPOINTS.values()))
                
                start = time.time()
                response = requests.get(endpoint, timeout=5)
                elapsed = (time.time() - start) * 1000
                
                self.request_count += 1
                self.phase_metrics[self.current_phase]['requests'] += 1
                
                if response.status_code != 200:
                    self.error_count += 1
                    self.phase_metrics[self.current_phase]['errors'] += 1
                
            except requests.exceptions.RequestException:
                self.error_count += 1
                self.phase_metrics[self.current_phase]['errors'] += 1
    
    def monitor_phase(self, phase_config: Dict):
        """フェーズの監視実行"""
        logger.info(f"フェーズ {phase_config['phase']} 監視開始")
        logger.info(f"  設定: {phase_config['traffic_percent']}% トラフィック")
        logger.info(f"  許容エラー率: {phase_config['max_error_rate']*100}%")
        logger.info(f"  許容レイテンシ: {phase_config['max_latency_ms']}ms")
        
        check_count = 0
        max_consecutive_failures = 0
        
        while self.monitoring_active and self.current_phase == phase_config['phase']:
            # ヘルスチェック実行
            health = self.check_service_health()
            health_dict = health.to_dict()
            self.health_check_history.append(health_dict)
            
            check_count += 1
            
            # ログ出力
            status_emoji = "🟢" if health.healthy_services == health.total_services else "🟡"
            logger.info(
                f"{status_emoji} ヘルスチェック #{check_count}: "
                f"{health.healthy_services}/{health.total_services} UP | "
                f"平均: {health.avg_latency:.1f}ms | "
                f"エラー: {', '.join(health.error_services) or 'なし'}"
            )
            
            # エラーが許容値を超えたかチェック
            if len(self.health_check_history) >= 3:
                recent = self.health_check_history[-3:]
                avg_error = sum(
                    (e['health_percent'] / 100.0) for e in recent
                ) / len(recent)
                
                if avg_error < (1.0 - phase_config['max_error_rate']):
                    max_consecutive_failures += 1
                    if max_consecutive_failures >= 2:
                        logger.error(f"エラー率が許容値を超過。フェーズ {phase_config['phase']} 停止。")
                        return False
                else:
                    max_consecutive_failures = 0
            
            # 次フェーズへ移行すべきかチェック
            if phase_config['duration_minutes'] > 0:
                elapsed = datetime.now() - self.phase_start_time
                duration = timedelta(minutes=phase_config['duration_minutes'])
                
                if elapsed >= duration:
                    if self.should_advance_phase():
                        logger.info(f"フェーズ {phase_config['phase']} 監視完了（正常）")
                        return True
            
            # スリープ
            time.sleep(phase_config['health_check_interval'])
        
        return True
    
    def run_production_launch(self):
        """本番運用開始メイン実行"""
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  ManaOS v1.0 本番運用開始              ║")
        logger.info("║  Production Traffic Controller         ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        
        self.start_time = datetime.now()
        
        # 初期ヘルスチェック
        logger.info("初期ヘルスチェック実行中...")
        initial_health = self.check_service_health()
        initial_dict = initial_health.to_dict()
        
        logger.info(f"")
        logger.info(f"初期状態: {initial_dict['healthy_count']}/{initial_dict['total_count']} サービス稼動")
        logger.info(f"レイテンシ: {initial_dict['avg_latency_ms']}ms")
        logger.info(f"")
        
        if initial_health.healthy_services < 6:
            logger.error("❌ 不十分なサービス稼働状態。本番運用開始を中止。")
            return False
        
        # フェーズ1開始
        logger.info("✅ 全サービス稼動確認。本番運用開始。")
        logger.info("")
        
        # 段階的トラフィック投入実行
        while self.current_phase <= 3 and self.monitoring_active:
            phase_config = self.get_current_phase_config()
            
            # フェーズモニタリング実行
            success = self.monitor_phase(phase_config)
            
            if not success:
                logger.error(f"フェーズ {phase_config['phase']} 監視失敗")
                return False
            
            # 次フェーズへ移行
            if not self.advance_phase():
                break
        
        # 最終レポート
        self.print_final_report()
        return True
    
    def print_final_report(self):
        """最終レポート出力"""
        total_elapsed = datetime.now() - self.start_time
        
        logger.warning("")
        logger.warning("╔════════════════════════════════════════╗")
        logger.warning("║  本番運用開始 - 最終レポート           ║")
        logger.warning("╚════════════════════════════════════════╝")
        logger.warning("")
        
        logger.info(f"総稼働時間: {total_elapsed}")
        logger.info(f"総リクエスト数: {self.request_count}")
        logger.info(f"総エラー数: {self.error_count}")
        logger.info(f"総成功率: {((self.request_count - self.error_count) / max(self.request_count, 1) * 100):.1f}%")
        logger.info("")
        
        logger.info("フェーズ別メトリクス:")
        for phase in range(1, 4):
            metrics = self.phase_metrics[phase]
            if metrics['requests'] > 0:
                success_rate = ((metrics['requests'] - metrics['errors']) / metrics['requests']) * 100
                logger.info(f"  フェーズ {phase}: {metrics['requests']} リクエスト | 成功率 {success_rate:.1f}%")
        
        logger.warning("")
        logger.warning("✅ 本番運用を正式に開始しました。")
        logger.warning("   すべてのフェーズが完了。本格稼動中です。")
        logger.warning("")


def main():
    """メイン実行"""
    controller = ProductionTrafficController()
    
    try:
        success = controller.run_production_launch()
        
        if success:
            logger.info("✅ 本番運用開始 - 成功")
            sys.exit(0)
        else:
            logger.error("❌ 本番運用開始 - 失敗")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n本番運用監視を中断しました。")
        controller.monitoring_active = False
        controller.print_final_report()
        sys.exit(0)
    except Exception as e:
        logger.exception(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
