#!/usr/bin/env python3
"""
Mana Auto Optimizer
自動最適化エンジン - システムリソースの自動調整・最適化
"""

import os
import psutil
import logging
import time
import subprocess
from datetime import datetime
from typing import Dict, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaAutoOptimizer:
    def __init__(self):
        self.config = {
            "memory_threshold": 80,  # メモリ80%で警告
            "memory_critical": 90,   # メモリ90%でクリーンアップ
            "disk_threshold": 85,    # ディスク85%で警告
            "cpu_threshold": 80,     # CPU80%で警告
            "check_interval": 60,    # 60秒ごとにチェック
            "cleanup_enabled": True,
            "notification_enabled": True
        }
        
        self.optimization_log = "/root/logs/auto_optimizer.log"
        os.makedirs("/root/logs", exist_ok=True)
        
        logger.info("🤖 Mana Auto Optimizer 初期化完了")
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "status": self._get_status(cpu_percent, self.config["cpu_threshold"])
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": memory.used / (1024**3),
                    "total_gb": memory.total / (1024**3),
                    "status": self._get_status(memory.percent, self.config["memory_threshold"])
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "status": self._get_status(disk.percent, self.config["disk_threshold"])
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"システム状態取得エラー: {e}")
            return {}
    
    def _get_status(self, value: float, threshold: float) -> str:
        """状態判定"""
        if value < threshold:
            return "ok"
        elif value < threshold + 10:
            return "warning"
        else:
            return "critical"
    
    def optimize_memory(self) -> Dict[str, Any]:
        """メモリ最適化"""
        logger.info("🧹 メモリ最適化を開始")
        
        try:
            before_memory = psutil.virtual_memory()
            actions = []
            
            # 1. Pythonキャッシュ削除
            result = subprocess.run(
                "find /root -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo 'done'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                actions.append("Python cache cleaned")
            
            # 2. システムキャッシュをドロップ（要root権限）
            try:
                subprocess.run("sync; echo 3 > /proc/sys/vm/drop_caches", shell=True, check=False)
                actions.append("System cache dropped")
            except Exception as e:
                logger.debug(f"キャッシュドロップスキップ: {e}")
            
            # 3. 一時ファイル削除
            temp_dirs = ["/tmp", "/var/tmp"]
            for temp_dir in temp_dirs:
                try:
                    result = subprocess.run(
                        f"find {temp_dir} -type f -mtime +7 -delete 2>/dev/null; echo 'done'",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        actions.append(f"Cleaned {temp_dir}")
                except Exception as e:
                    logger.debug(f"一時ファイル削除エラー ({temp_dir}): {e}")
            
            time.sleep(2)  # システムが安定するまで待機
            
            after_memory = psutil.virtual_memory()
            freed_mb = (before_memory.used - after_memory.used) / (1024**2)
            
            result = {
                "success": True,
                "before_percent": round(before_memory.percent, 1),
                "after_percent": round(after_memory.percent, 1),
                "freed_mb": round(freed_mb, 2),
                "actions": actions
            }
            
            logger.info(f"✅ メモリ最適化完了: {freed_mb:.2f}MB回収")
            self._log_optimization("memory", result)
            
            return result
            
        except Exception as e:
            logger.error(f"メモリ最適化エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def optimize_disk(self) -> Dict[str, Any]:
        """ディスク最適化"""
        logger.info("💾 ディスク最適化を開始")
        
        try:
            before_disk = psutil.disk_usage('/')
            actions = []
            
            # 1. 古いログファイル圧縮
            try:
                result = subprocess.run(
                    "find /root/logs -name '*.log' -mtime +7 -exec gzip {} \; 2>/dev/null; echo 'done'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    actions.append("Old logs compressed")
            except Exception as e:
                logger.debug(f"ログ圧縮エラー: {e}")
            
            # 2. APTキャッシュクリーンアップ
            try:
                subprocess.run("apt-get clean 2>/dev/null", shell=True, check=False, timeout=30)
                actions.append("APT cache cleaned")
            except Exception as e:
                logger.debug(f"APTキャッシュクリーンアップスキップ: {e}")
            
            # 3. Dockerイメージの未使用削除
            try:
                result = subprocess.run(
                    "docker image prune -f 2>/dev/null",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0 and "Total reclaimed space" in result.stdout:
                    actions.append("Docker images pruned")
            except Exception as e:
                logger.debug(f"Dockerイメージ削除スキップ: {e}")
            
            time.sleep(2)
            
            after_disk = psutil.disk_usage('/')
            freed_gb = (before_disk.used - after_disk.used) / (1024**3)
            
            result = {
                "success": True,
                "before_percent": round(before_disk.percent, 1),
                "after_percent": round(after_disk.percent, 1),
                "freed_gb": round(freed_gb, 2),
                "actions": actions
            }
            
            logger.info(f"✅ ディスク最適化完了: {freed_gb:.2f}GB回収")
            self._log_optimization("disk", result)
            
            return result
            
        except Exception as e:
            logger.error(f"ディスク最適化エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def check_and_optimize(self) -> Dict[str, Any]:
        """状態チェックと自動最適化"""
        logger.info("🔍 システムチェック開始")
        
        status = self.get_system_status()
        optimizations = []
        
        # メモリチェック
        if status["memory"]["status"] == "critical":
            logger.warning("⚠️ メモリ使用率がCRITICAL: {}%".format(status["memory"]["percent"]))
            if self.config["cleanup_enabled"]:
                result = self.optimize_memory()
                optimizations.append({"type": "memory", "result": result})
        elif status["memory"]["status"] == "warning":
            logger.info("⚡ メモリ使用率がWARNING: {}%".format(status["memory"]["percent"]))
        
        # ディスクチェック
        if status["disk"]["status"] in ["warning", "critical"]:
            logger.warning("⚠️ ディスク使用率が{}：{}%".format(
                status["disk"]["status"].upper(), status["disk"]["percent"]
            ))
            if self.config["cleanup_enabled"]:
                result = self.optimize_disk()
                optimizations.append({"type": "disk", "result": result})
        
        # CPUチェック
        if status["cpu"]["status"] in ["warning", "critical"]:
            logger.warning("⚠️ CPU使用率が{}：{}%".format(
                status["cpu"]["status"].upper(), status["cpu"]["percent"]
            ))
            # CPU最適化は慎重に（プロセスkillなどは危険）
            optimizations.append({
                "type": "cpu",
                "result": {"success": False, "message": "Manual intervention required"}
            })
        
        return {
            "status": status,
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _log_optimization(self, opt_type: str, result: Dict[str, Any]):
        """最適化ログ記録"""
        try:
            log_entry = {
                "type": opt_type,
                "timestamp": datetime.now().isoformat(),
                "result": result
            }
            
            with open(self.optimization_log, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"ログ記録エラー: {e}")
    
    def run_continuous(self):
        """連続監視モード"""
        logger.info("🔄 連続監視モード開始")
        
        try:
            while True:
                result = self.check_and_optimize()
                
                if result["optimizations"]:
                    logger.info(f"✅ {len(result['optimizations'])}個の最適化を実行")
                
                time.sleep(self.config["check_interval"])
                
        except KeyboardInterrupt:
            logger.info("⏹️ 連続監視モード停止")
        except Exception as e:
            logger.error(f"連続監視エラー: {e}")
    
    def get_optimization_stats(self, days: int = 7) -> Dict[str, Any]:
        """最適化統計取得"""
        try:
            if not os.path.exists(self.optimization_log):
                return {"total_optimizations": 0, "by_type": {}}
            
            with open(self.optimization_log, 'r') as f:
                lines = f.readlines()
            
            optimizations = []
            for line in lines:
                try:
                    entry = json.loads(line)
                    optimizations.append(entry)
                except IOError:
                    continue
            
            # 統計計算
            total = len(optimizations)
            by_type = {}
            total_freed_memory = 0
            total_freed_disk = 0
            
            for opt in optimizations:
                opt_type = opt.get("type", "unknown")
                by_type[opt_type] = by_type.get(opt_type, 0) + 1
                
                if opt_type == "memory":
                    freed = opt.get("result", {}).get("freed_mb", 0)
                    total_freed_memory += freed
                elif opt_type == "disk":
                    freed = opt.get("result", {}).get("freed_gb", 0)
                    total_freed_disk += freed
            
            return {
                "total_optimizations": total,
                "by_type": by_type,
                "total_freed_memory_mb": round(total_freed_memory, 2),
                "total_freed_disk_gb": round(total_freed_disk, 2)
            }
            
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {}

def main():
    optimizer = ManaAutoOptimizer()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            status = optimizer.get_system_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
        
        elif command == "memory":
            result = optimizer.optimize_memory()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "disk":
            result = optimizer.optimize_disk()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "check":
            result = optimizer.check_and_optimize()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "stats":
            stats = optimizer.get_optimization_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        elif command == "run":
            optimizer.run_continuous()
        
        else:
            print("Usage: mana_auto_optimizer.py [status|memory|disk|check|stats|run]")
    else:
        # デフォルトはチェック実行
        result = optimizer.check_and_optimize()
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

