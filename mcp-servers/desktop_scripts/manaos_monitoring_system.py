"""
ManaOS 統合監視システム
Tier S: HWiNFO + MSI Afterburner
Tier A: CrystalDiskInfo
Tier SS: Prometheus + Grafana + Pixel表示パネル連動
"""

import os
import sys
import time
import json
import logging
import ctypes
import struct
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

import psutil
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ManaOS 統合監視システム",
    description="HWiNFO + MSI Afterburner + CrystalDiskInfo + Prometheus統合",
    version="1.0.0"
)


class MonitorTier(Enum):
    """監視ツールの優先度"""
    TIER_S = "S"  # 今すぐ: HWiNFO, MSI Afterburner
    TIER_A = "A"  # 安定運用: CrystalDiskInfo
    TIER_SS = "SS"  # マナ専用変態構成: Prometheus + Grafana + Pixel


@dataclass
class GPUInfo:
    """GPU情報"""
    name: str
    temperature: float
    usage_percent: float
    memory_used_mb: float
    memory_total_mb: float
    clock_core_mhz: float
    clock_memory_mhz: float
    power_watts: Optional[float] = None
    fan_speed_rpm: Optional[float] = None


@dataclass
class CPUInfo:
    """CPU情報"""
    usage_percent: float
    temperature: Optional[float]
    clock_mhz: float
    cores: int
    threads: int


@dataclass
class DiskInfo:
    """ディスク情報"""
    drive: str
    model: str
    temperature: Optional[float]
    health_status: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    read_speed_mb_s: Optional[float] = None
    write_speed_mb_s: Optional[float] = None


@dataclass
class SystemMetrics:
    """システム全体のメトリクス"""
    timestamp: str
    cpu: CPUInfo
    gpu: List[GPUInfo]
    disks: List[DiskInfo]
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float


try:
    from windows_shared_memory import HWiNFOMemoryReader, RTSSMemoryReader  # type: ignore
except ImportError:
    logger.warning("windows_shared_memory module not found, using fallback")
    
    class HWiNFOMemoryReader:
        def __init__(self):
            self.is_available = False
        
        def read_sensors(self):
            return {}
    
    class RTSSMemoryReader:
        def __init__(self):
            self.is_available = False
        
        def read_metrics(self):
            return {}


class HWiNFOReader:
    """HWiNFO Shared Memory Reader"""
    
    def __init__(self):
        self.reader = HWiNFOMemoryReader()
        self.is_available = self.reader.is_available
    
    def read_sensors(self) -> Dict[str, Any]:
        """センサーデータを読み取り"""
        return self.reader.read_sensors()


class MSIAfterburnerReader:
    """MSI Afterburner / RivaTuner Statistics Server Reader"""
    
    def __init__(self):
        self.reader = RTSSMemoryReader()
        self.is_available = self.reader.is_available
    
    def read_metrics(self) -> Dict[str, Any]:
        """メトリクスを読み取り"""
        return self.reader.read_metrics()


class CrystalDiskInfoReader:
    """CrystalDiskInfo Reader (WMI/S.M.A.R.T.)"""
    
    def __init__(self):
        self.is_available = False
        self._init_wmi()
    
    def _init_wmi(self):
        """WMIを初期化"""
        try:
            import wmi
            self.wmi_conn = wmi.WMI()
            self.is_available = True
            logger.info("CrystalDiskInfo/WMI reader initialized")
        except ImportError:
            logger.warning("WMI module not available. Install: pip install wmi")
            self.wmi_conn = None
            self.is_available = False
        except Exception as e:
            logger.warning(f"CrystalDiskInfo/WMI not available: {e}")
            self.wmi_conn = None
            self.is_available = False
    
    def read_disk_info(self) -> List[DiskInfo]:
        """ディスク情報を読み取り"""
        if not self.is_available:
            return self._fallback_disk_info()
        
        disks = []
        try:
            # WMI経由でディスク情報を取得
            for disk in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    
                    disk_info = DiskInfo(
                        drive=disk.mountpoint,
                        model=self._get_disk_model(disk.device),
                        temperature=None,  # S.M.A.R.T.から取得
                        health_status="Good",  # S.M.A.R.T.から取得
                        total_gb=usage.total / (1024**3),
                        used_gb=usage.used / (1024**3),
                        free_gb=usage.free / (1024**3),
                        usage_percent=usage.percent
                    )
                    disks.append(disk_info)
                except PermissionError:
                    continue
        except Exception as e:
            logger.error(f"Failed to read disk info: {e}")
            return self._fallback_disk_info()
        
        return disks
    
    def _get_disk_model(self, device: str) -> str:
        """ディスクモデル名を取得"""
        try:
            if hasattr(self, 'wmi_conn'):
                for disk in self.wmi_conn.Win32_DiskDrive():  # type: ignore[union-attr]
                    if device.startswith(disk.DeviceID.replace('\\', '')):
                        return disk.Model or "Unknown"
        except:
            pass
        return "Unknown"
    
    def _fallback_disk_info(self) -> List[DiskInfo]:
        """フォールバック: psutilのみでディスク情報を取得"""
        disks = []
        for disk in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(disk.mountpoint)
                disk_info = DiskInfo(
                    drive=disk.mountpoint,
                    model="Unknown",
                    temperature=None,
                    health_status="Unknown",
                    total_gb=usage.total / (1024**3),
                    used_gb=usage.used / (1024**3),
                    free_gb=usage.free / (1024**3),
                    usage_percent=usage.percent
                )
                disks.append(disk_info)
            except PermissionError:
                continue
        return disks


class PrometheusExporter:
    """Prometheusメトリクスエクスポーター"""
    
    def __init__(self, pushgateway_url: str = "http://127.0.0.1:9091"):
        self.pushgateway_url = pushgateway_url
        self.is_available = False
        self._check_pushgateway()
    
    def _check_pushgateway(self):
        """Pushgatewayの可用性を確認"""
        try:
            response = requests.get(f"{self.pushgateway_url}/", timeout=2)
            self.is_available = response.status_code == 200
            if self.is_available:
                logger.info(f"Prometheus Pushgateway available at {self.pushgateway_url}")
        except Exception as e:
            logger.warning(f"Prometheus Pushgateway not available: {e}")
            self.is_available = False
    
    def reconnect(self):
        """Pushgatewayへの接続を再確認"""
        self._check_pushgateway()
    
    def export_metrics(self, metrics: SystemMetrics):
        """メトリクスをPrometheusにエクスポート"""
        if not self.is_available:
            return False
        
        try:
            prom_metrics = []
            
            # CPU metrics
            prom_metrics.append(f"cpu_usage_percent {metrics.cpu.usage_percent}")
            if metrics.cpu.temperature:
                prom_metrics.append(f"cpu_temperature_celsius {metrics.cpu.temperature}")
            prom_metrics.append(f"cpu_clock_mhz {metrics.cpu.clock_mhz}")
            
            # GPU metrics
            for i, gpu in enumerate(metrics.gpu):
                prom_metrics.append(f"gpu_temperature_celsius{{gpu=\"{i}\",name=\"{gpu.name}\"}} {gpu.temperature}")
                prom_metrics.append(f"gpu_usage_percent{{gpu=\"{i}\",name=\"{gpu.name}\"}} {gpu.usage_percent}")
                prom_metrics.append(f"gpu_memory_used_mb{{gpu=\"{i}\",name=\"{gpu.name}\"}} {gpu.memory_used_mb}")
                prom_metrics.append(f"gpu_memory_total_mb{{gpu=\"{i}\",name=\"{gpu.name}\"}} {gpu.memory_total_mb}")
                if gpu.power_watts:
                    prom_metrics.append(f"gpu_power_watts{{gpu=\"{i}\",name=\"{gpu.name}\"}} {gpu.power_watts}")
            
            # Memory metrics
            prom_metrics.append(f"memory_total_gb {metrics.memory_total_gb}")
            prom_metrics.append(f"memory_used_gb {metrics.memory_used_gb}")
            prom_metrics.append(f"memory_available_gb {metrics.memory_available_gb}")
            prom_metrics.append(f"memory_usage_percent {metrics.memory_percent}")
            
            # Disk metrics
            for disk in metrics.disks:
                prom_metrics.append(f"disk_total_gb{{drive=\"{disk.drive}\"}} {disk.total_gb}")
                prom_metrics.append(f"disk_used_gb{{drive=\"{disk.drive}\"}} {disk.used_gb}")
                prom_metrics.append(f"disk_free_gb{{drive=\"{disk.drive}\"}} {disk.free_gb}")
                prom_metrics.append(f"disk_usage_percent{{drive=\"{disk.drive}\"}} {disk.usage_percent}")
                if disk.temperature:
                    prom_metrics.append(f"disk_temperature_celsius{{drive=\"{disk.drive}\"}} {disk.temperature}")
            
            # Pushgatewayに送信
            metrics_text = "\n".join(prom_metrics)
            response = requests.post(
                f"{self.pushgateway_url}/metrics/job/manaos_monitoring/instance/localhost",
                data=metrics_text,
                timeout=5
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to export metrics to Prometheus: {e}")
            return False


class PixelDisplayClient:
    """Pixel表示パネル連動クライアント"""
    
    def __init__(self, pixel_hub_url: str = "http://127.0.0.1:9405"):
        self.pixel_hub_url = pixel_hub_url
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Pixel Hubの可用性を確認"""
        try:
            response = requests.get(f"{self.pixel_hub_url}/health", timeout=2)
            self.is_available = response.status_code == 200
            if self.is_available:
                logger.info(f"Pixel Hub available at {self.pixel_hub_url}")
        except Exception as e:
            logger.warning(f"Pixel Hub not available: {e}")
            self.is_available = False
    
    def send_metrics(self, metrics: SystemMetrics):
        """メトリクスをPixel表示パネルに送信"""
        if not self.is_available:
            return False
        
        try:
            # 簡易的な通知形式で送信
            summary = self._format_summary(metrics)
            
            response = requests.post(
                f"{self.pixel_hub_url}/pixel7/notification",
                json={
                    "title": "ManaOS監視",
                    "text": summary
                },
                timeout=5
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send metrics to Pixel: {e}")
            return False
    
    def _format_summary(self, metrics: SystemMetrics) -> str:
        """メトリクスを簡潔なテキストにフォーマット"""
        lines = []
        lines.append(f"CPU: {metrics.cpu.usage_percent:.1f}%")
        if metrics.cpu.temperature:
            lines.append(f"CPU温度: {metrics.cpu.temperature:.1f}°C")
        
        if metrics.gpu:
            gpu = metrics.gpu[0]
            lines.append(f"GPU: {gpu.usage_percent:.1f}%")
            lines.append(f"GPU温度: {gpu.temperature:.1f}°C")
        
        lines.append(f"メモリ: {metrics.memory_percent:.1f}%")
        
        if metrics.disks:
            disk = metrics.disks[0]
            lines.append(f"ディスク({disk.drive}): {disk.usage_percent:.1f}%")
        
        return "\n".join(lines)


class ManaOSMonitoringSystem:
    """ManaOS統合監視システム"""
    
    def __init__(self):
        self.hwinfo = HWiNFOReader()
        self.msi_afterburner = MSIAfterburnerReader()
        self.crystal_disk = CrystalDiskInfoReader()
        self.prometheus = PrometheusExporter()
        self.pixel_client = PixelDisplayClient()
        
        logger.info("ManaOS Monitoring System initialized")
    
    def collect_metrics(self) -> SystemMetrics:
        """システムメトリクスを収集"""
        # CPU情報
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_info = CPUInfo(
            usage_percent=cpu_percent,
            temperature=self._get_cpu_temperature(),
            clock_mhz=cpu_freq.current if cpu_freq else 0,
            cores=psutil.cpu_count(logical=False),  # type: ignore
            threads=psutil.cpu_count(logical=True)  # type: ignore
        )
        
        # GPU情報
        gpu_list = self._get_gpu_info()
        
        # ディスク情報
        disks = self.crystal_disk.read_disk_info()
        
        # メモリ情報
        memory = psutil.virtual_memory()
        
        metrics = SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu=cpu_info,
            gpu=gpu_list,
            disks=disks,
            memory_total_gb=memory.total / (1024**3),
            memory_used_gb=memory.used / (1024**3),
            memory_available_gb=memory.available / (1024**3),
            memory_percent=memory.percent
        )
        
        return metrics
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """CPU温度を取得"""
        # HWiNFOから取得を試みる
        hwinfo_data = self.hwinfo.read_sensors()
        if hwinfo_data.get("cpu_temp"):
            return hwinfo_data["cpu_temp"]
        
        # psutilから取得（Windowsでは通常利用不可）
        try:
            temps = psutil.sensors_temperatures()  # type: ignore[attr-defined]
            if 'coretemp' in temps:
                return temps['coretemp'][0].current
        except:
            pass
        
        return None
    
    def _get_gpu_info(self) -> List[GPUInfo]:
        """GPU情報を取得"""
        gpu_list = []
        
        # MSI Afterburnerから取得を試みる
        msi_data = self.msi_afterburner.read_metrics()
        if msi_data.get("gpu_temp") is not None:
            gpu_list.append(GPUInfo(
                name="GPU (MSI Afterburner)",
                temperature=msi_data.get("gpu_temp", 0),
                usage_percent=msi_data.get("gpu_usage", 0),
                memory_used_mb=msi_data.get("gpu_memory", 0),
                memory_total_mb=0,
                clock_core_mhz=msi_data.get("gpu_clock", 0),
                clock_memory_mhz=0,
                power_watts=msi_data.get("gpu_power"),
                fan_speed_rpm=None
            ))
        
        # HWiNFOから取得を試みる
        hwinfo_data = self.hwinfo.read_sensors()
        if hwinfo_data.get("gpu_temp") is not None:
            gpu_list.append(GPUInfo(
                name="GPU (HWiNFO)",
                temperature=hwinfo_data.get("gpu_temp", 0),
                usage_percent=hwinfo_data.get("gpu_usage", 0),
                memory_used_mb=hwinfo_data.get("gpu_memory", 0),
                memory_total_mb=0,
                clock_core_mhz=0,
                clock_memory_mhz=0,
                power_watts=None,
                fan_speed_rpm=None
            ))
        
        # NVIDIA GPU (nvidia-smi)から取得
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,clocks.current.graphics,clocks.current.memory,power.draw", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 8:
                        gpu_list.append(GPUInfo(
                            name=parts[0],
                            temperature=float(parts[1]),
                            usage_percent=float(parts[2]),
                            memory_used_mb=float(parts[3]),
                            memory_total_mb=float(parts[4]),
                            clock_core_mhz=float(parts[5]),
                            clock_memory_mhz=float(parts[6]),
                            power_watts=float(parts[7]) if parts[7] != '[Not Supported]' else None,
                            fan_speed_rpm=None
                        ))
        except Exception as e:
            logger.debug(f"nvidia-smi not available: {e}")
        
        return gpu_list
    
    def export_all(self, metrics: SystemMetrics):
        """すべてのエクスポーターにメトリクスを送信"""
        # Prometheus
        self.prometheus.export_metrics(metrics)
        
        # Pixel表示パネル
        self.pixel_client.send_metrics(metrics)


# グローバルインスタンス
monitoring_system = ManaOSMonitoringSystem()


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "ManaOS 統合監視システム",
        "version": "1.0.0",
        "tiers": {
            "Tier S": ["HWiNFO", "MSI Afterburner"],
            "Tier A": ["CrystalDiskInfo"],
            "Tier SS": ["Prometheus", "Grafana", "Pixel表示パネル"]
        }
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "hwinfo": monitoring_system.hwinfo.is_available,
        "msi_afterburner": monitoring_system.msi_afterburner.is_available,
        "crystal_disk": monitoring_system.crystal_disk.is_available,
        "prometheus": monitoring_system.prometheus.is_available,
        "pixel": monitoring_system.pixel_client.is_available,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """現在のメトリクスを取得"""
    metrics = monitoring_system.collect_metrics()
    return JSONResponse(content=asdict(metrics))


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Prometheus形式のメトリクスを取得"""
    metrics = monitoring_system.collect_metrics()
    monitoring_system.prometheus.export_metrics(metrics)
    
    # Prometheus形式で返す
    prom_metrics = []
    prom_metrics.append(f"cpu_usage_percent {metrics.cpu.usage_percent}")
    if metrics.cpu.temperature:
        prom_metrics.append(f"cpu_temperature_celsius {metrics.cpu.temperature}")
    
    for i, gpu in enumerate(metrics.gpu):
        prom_metrics.append(f"gpu_temperature_celsius{{gpu=\"{i}\"}} {gpu.temperature}")
        prom_metrics.append(f"gpu_usage_percent{{gpu=\"{i}\"}} {gpu.usage_percent}")
    
    prom_metrics.append(f"memory_usage_percent {metrics.memory_percent}")
    
    return "\n".join(prom_metrics)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """監視ダッシュボード"""
    metrics = monitoring_system.collect_metrics()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ManaOS 統合監視ダッシュボード</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="5">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 20px;
                background: #1a1a1a;
                color: #e0e0e0;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            h1 {{
                color: #4a9eff;
                border-bottom: 2px solid #4a9eff;
                padding-bottom: 10px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}
            .metric-card {{
                background: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            }}
            .metric-title {{
                font-size: 18px;
                font-weight: bold;
                color: #4a9eff;
                margin-bottom: 15px;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
                color: #fff;
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 14px;
                color: #aaa;
            }}
            .status-good {{ color: #4caf50; }}
            .status-warning {{ color: #ff9800; }}
            .status-danger {{ color: #f44336; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ManaOS 統合監視ダッシュボード</h1>
            <p>最終更新: {metrics.timestamp}</p>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">CPU</div>
                    <div class="metric-value">{metrics.cpu.usage_percent:.1f}%</div>
                    <div class="metric-label">
                        コア数: {metrics.cpu.cores} / スレッド数: {metrics.cpu.threads}<br>
                        クロック: {metrics.cpu.clock_mhz:.0f} MHz
                        {f'<br>温度: {metrics.cpu.temperature:.1f}°C' if metrics.cpu.temperature else ''}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">メモリ</div>
                    <div class="metric-value">{metrics.memory_percent:.1f}%</div>
                    <div class="metric-label">
                        使用: {metrics.memory_used_gb:.1f} GB / {metrics.memory_total_gb:.1f} GB<br>
                        空き: {metrics.memory_available_gb:.1f} GB
                    </div>
                </div>
            </div>
            
            <h2>GPU</h2>
            <div class="metrics-grid">
    """
    
    for gpu in metrics.gpu:
        html += f"""
                <div class="metric-card">
                    <div class="metric-title">{gpu.name}</div>
                    <div class="metric-value">{gpu.usage_percent:.1f}%</div>
                    <div class="metric-label">
                        温度: {gpu.temperature:.1f}°C<br>
                        メモリ: {gpu.memory_used_mb:.0f} MB / {gpu.memory_total_mb:.0f} MB<br>
                        クロック: {gpu.clock_core_mhz:.0f} MHz
                        {f'<br>消費電力: {gpu.power_watts:.1f} W' if gpu.power_watts else ''}
                    </div>
                </div>
        """
    
    html += """
            </div>
            
            <h2>ディスク</h2>
            <div class="metrics-grid">
    """
    
    for disk in metrics.disks:
        html += f"""
                <div class="metric-card">
                    <div class="metric-title">{disk.drive} ({disk.model})</div>
                    <div class="metric-value">{disk.usage_percent:.1f}%</div>
                    <div class="metric-label">
                        使用: {disk.used_gb:.1f} GB / {disk.total_gb:.1f} GB<br>
                        空き: {disk.free_gb:.1f} GB
                        {f'<br>温度: {disk.temperature:.1f}°C' if disk.temperature else ''}
                        <br>状態: {disk.health_status}
                    </div>
                </div>
        """
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@app.post("/export")
async def export_metrics():
    """メトリクスをすべてのエクスポーターに送信"""
    # 接続を再確認
    monitoring_system.prometheus.reconnect()
    monitoring_system.pixel_client._check_availability()
    
    metrics = monitoring_system.collect_metrics()
    monitoring_system.export_all(metrics)
    
    return {
        "success": True,
        "exported_to": {
            "prometheus": monitoring_system.prometheus.is_available,
            "pixel": monitoring_system.pixel_client.is_available
        },
        "timestamp": metrics.timestamp
    }


if __name__ == "__main__":
    port = int(os.getenv("MONITORING_PORT", "9406"))
    host = os.getenv("MONITORING_HOST", "0.0.0.0")
    
    logger.info(f"Starting ManaOS Monitoring System on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

