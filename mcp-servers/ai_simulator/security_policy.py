"""
AI Simulator Security Policy
安全制御とリソース管理の実装
"""

import os
import psutil
import signal
import logging
from typing import List
from dataclasses import dataclass
from pathlib import Path
import time

@dataclass
class ResourceLimits:
    """リソース制限設定"""
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    max_disk_mb: int = 1000
    max_processes: int = 10
    max_file_descriptors: int = 100

@dataclass
class SecurityPolicy:
    """セキュリティポリシー設定"""
    allowed_directories: List[str]
    blocked_commands: List[str]
    max_execution_time: int = 300  # 5分
    enable_network_isolation: bool = True
    enable_file_monitoring: bool = True

class SecurityManager:
    """セキュリティ管理クラス"""
    
    def __init__(self, policy: SecurityPolicy, limits: ResourceLimits):
        self.policy = policy
        self.limits = limits
        self.start_time = time.time()
        self.process_monitor = ProcessMonitor(limits)
        self.file_monitor = FileMonitor(policy)
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('ai_simulator_security')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/security.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def check_execution_time(self) -> bool:
        """実行時間チェック"""
        elapsed = time.time() - self.start_time
        if elapsed > self.policy.max_execution_time:
            self.logger.warning(f"Execution time exceeded: {elapsed}s")
            return False
        return True
    
    def check_resource_usage(self) -> bool:
        """リソース使用量チェック"""
        return self.process_monitor.check_limits()
    
    def check_file_access(self, file_path: str) -> bool:
        """ファイルアクセスチェック"""
        return self.file_monitor.is_allowed(file_path)
    
    def emergency_stop(self, reason: str):
        """緊急停止"""
        self.logger.critical(f"EMERGENCY STOP: {reason}")
        os.kill(os.getpid(), signal.SIGTERM)

class ProcessMonitor:
    """プロセス監視クラス"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.process = psutil.Process()
    
    def check_limits(self) -> bool:
        """リソース制限チェック"""
        try:
            # メモリ使用量チェック
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > self.limits.max_memory_mb:
                return False
            
            # CPU使用量チェック
            cpu_percent = self.process.cpu_percent()
            if cpu_percent > self.limits.max_cpu_percent:
                return False
            
            # プロセス数チェック
            children = self.process.children(recursive=True)
            if len(children) > self.limits.max_processes:
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Resource check failed: {e}")
            return False

class FileMonitor:
    """ファイル監視クラス"""
    
    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
        self.allowed_paths = [Path(p) for p in policy.allowed_directories]
    
    def is_allowed(self, file_path: str) -> bool:
        """ファイルアクセス許可チェック"""
        path = Path(file_path).resolve()
        
        # 許可されたディレクトリ内かチェック
        for allowed_path in self.allowed_paths:
            try:
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        
        return False

class ContainerManager:
    """コンテナ管理クラス"""
    
    def __init__(self):
        self.security_manager = None
        self.is_running = False
    
    def initialize_security(self):
        """セキュリティシステム初期化"""
        # デフォルト設定
        policy = SecurityPolicy(
            allowed_directories=[
                '/app/workspace',
                '/app/logs',
                '/tmp'
            ],
            blocked_commands=[
                'rm -rf /',
                'sudo',
                'su',
                'chmod 777',
                'dd if=/dev/zero'
            ]
        )
        
        limits = ResourceLimits()
        
        self.security_manager = SecurityManager(policy, limits)
        self.is_running = True
        
        logging.info("Security system initialized")
    
    def start_monitoring(self):
        """監視開始"""
        if not self.security_manager:
            self.initialize_security()
        
        while self.is_running:
            try:
                # 実行時間チェック
                if not self.security_manager.check_execution_time():  # type: ignore[union-attr]
                    self.security_manager.emergency_stop("Execution time exceeded")  # type: ignore[union-attr]
                    break
                
                # リソース使用量チェック
                if not self.security_manager.check_resource_usage():  # type: ignore[union-attr]
                    self.security_manager.emergency_stop("Resource limit exceeded")  # type: ignore[union-attr]
                    break
                
                time.sleep(1)  # 1秒間隔でチェック
                
            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                self.security_manager.emergency_stop(f"Monitoring error: {e}")  # type: ignore[union-attr]
                break
    
    def stop(self):
        """停止"""
        self.is_running = False
        logging.info("Container manager stopped")

if __name__ == "__main__":
    # ログディレクトリ作成
    os.makedirs('/app/logs', exist_ok=True)
    
    # セキュリティシステム起動
    manager = ContainerManager()
    manager.start_monitoring()