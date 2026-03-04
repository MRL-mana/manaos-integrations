"""
メトリクスエクスポートタスク（Stage B 安全タスク）
"""

import logging
from typing import Dict, Any
from datetime import datetime
import os
import requests

logger = logging.getLogger(__name__)

def export_metrics(format: str = "json", output_dir: str = "/tmp") -> Dict[str, Any]:
    """Prometheusメトリクスをエクスポート"""
    logger.info(f"Exporting metrics in {format} format")

    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

    result = {
        "format": format,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "message": "",
        "metrics_count": 0
    }

    try:
        # Prometheus APIからメトリクス取得
        query_url = f"{prometheus_url}/api/v1/query"
        params = {"query": "{__name__=~'.+'}"}  # 全メトリクス取得

        response = requests.get(query_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            metrics = data.get("data", {}).get("result", [])
            result["metrics_count"] = len(metrics)

            # ファイル保存（簡易実装）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format == "json":
                import json
                output_file = f"{output_dir}/metrics_export_{timestamp}.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                result["output_file"] = output_file
            elif format == "prometheus":
                output_file = f"{output_dir}/metrics_export_{timestamp}.txt"
                # Prometheus形式でエクスポート（簡易実装）
                with open(output_file, "w") as f:
                    for metric in metrics:
                        f.write(f"{metric.get('metric', {})}\n")
                result["output_file"] = output_file

            result["message"] = f"Exported {len(metrics)} metrics to {result.get('output_file', 'memory')}"
            logger.info(f"Metrics exported successfully: {len(metrics)} metrics")
        else:
            result["status"] = "error"
            result["message"] = f"Prometheus API returned {response.status_code}"
            logger.error(f"Metrics export failed: {response.status_code}")

    except requests.exceptions.RequestException as e:
        result["status"] = "error"
        result["message"] = f"Failed to export metrics: {str(e)}"
        logger.error(f"Metrics export failed: {e}")
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Unexpected error: {str(e)}"
        logger.error(f"Metrics export error: {e}")

    return result






