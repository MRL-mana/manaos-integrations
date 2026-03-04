"""
ManaOS監視システム 自動エクスポーター
定期的にメトリクスをPrometheusとPixelにエクスポート
"""

import time
import requests
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringExporter:
    """監視システム自動エクスポーター"""
    
    def __init__(
        self,
        monitoring_url: str = "http://127.0.0.1:9406",
        interval: int = 300  # 5分間隔
    ):
        self.monitoring_url = monitoring_url
        self.interval = interval
        self.running = False
    
    def check_monitoring_system(self) -> bool:
        """監視システムが起動しているか確認"""
        try:
            response = requests.get(
                f"{self.monitoring_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Monitoring system not available: {e}")
            return False
    
    def export_metrics(self) -> bool:
        """メトリクスをエクスポート"""
        try:
            response = requests.post(
                f"{self.monitoring_url}/export",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Exported metrics - "
                    f"Prometheus: {result.get('exported_to', {}).get('prometheus', False)}, "
                    f"Pixel: {result.get('exported_to', {}).get('pixel', False)}"
                )
                return True
            else:
                logger.warning(f"Export failed with status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False
    
    def run(self):
        """エクスポーターを実行"""
        logger.info(f"Starting Monitoring Exporter (interval: {self.interval}s)")
        
        if not self.check_monitoring_system():
            logger.error("Monitoring system is not available. Please start it first.")
            return
        
        self.running = True
        export_count = 0
        success_count = 0
        
        try:
            while self.running:
                export_count += 1
                logger.info(f"Export #{export_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                if self.export_metrics():
                    success_count += 1
                
                logger.info(f"Success rate: {success_count}/{export_count} ({success_count*100/export_count:.1f}%)")
                
                # 待機
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Stopping exporter...")
            self.running = False
        except Exception as e:
            logger.error(f"Exporter error: {e}")
            self.running = False
    
    def stop(self):
        """エクスポーターを停止"""
        self.running = False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ManaOS Monitoring Exporter")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:9406",
        help="Monitoring system URL"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Export interval in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    exporter = MonitoringExporter(
        monitoring_url=args.url,
        interval=args.interval
    )
    
    exporter.run()




