"""
AI Simulator Container Manager
Dockerコンテナの管理と制御
"""

import docker
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ContainerStatus:
    """コンテナ状態"""
    container_id: str
    status: str
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, int]
    disk_io: Dict[str, int]
    uptime: float

class ContainerManager:
    """コンテナ管理クラス"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.containers: Dict[str, docker.models.containers.Container] = {}
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('container_manager')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/container.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def create_sandbox_container(self, image_name: str = "ai-simulator") -> str:
        """サンドボックスコンテナ作成"""
        try:
            # コンテナ設定
            container_config = {
                'image': image_name,
                'name': f'ai-simulator-{int(time.time())}',
                'detach': True,
                'network_mode': 'ai-simulator-network',
                'mem_limit': '512m',
                'cpu_quota': 100000,  # 1 CPU core
                'cpu_period': 100000,
                'read_only': True,
                'tmpfs': {
                    '/tmp': 'noexec,nosuid,size=100m',
                    '/var/tmp': 'noexec,nosuid,size=100m'
                },
                'volumes': {
                    '/app/workspace': {'bind': '/app/workspace', 'mode': 'rw'},
                    '/app/logs': {'bind': '/app/logs', 'mode': 'rw'}
                },
                'environment': {
                    'AI_SIMULATOR_MODE': 'sandbox',
                    'PYTHONPATH': '/app'
                },
                'security_opt': ['no-new-privileges:true'],
                'cap_drop': ['ALL'],
                'cap_add': []
            }
            
            # コンテナ作成
            container = self.client.containers.run(**container_config)
            container_id = container.short_id
            
            self.containers[container_id] = container
            self.logger.info(f"Created sandbox container: {container_id}")
            
            return container_id
            
        except Exception as e:
            self.logger.error(f"Failed to create container: {e}")
            raise
    
    def start_container(self, container_id: str) -> bool:
        """コンテナ開始"""
        try:
            if container_id in self.containers:
                container = self.containers[container_id]
                container.start()
                self.logger.info(f"Started container: {container_id}")
                return True
            else:
                self.logger.error(f"Container not found: {container_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start container {container_id}: {e}")
            return False
    
    def stop_container(self, container_id: str) -> bool:
        """コンテナ停止"""
        try:
            if container_id in self.containers:
                container = self.containers[container_id]
                container.stop(timeout=10)
                self.logger.info(f"Stopped container: {container_id}")
                return True
            else:
                self.logger.error(f"Container not found: {container_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to stop container {container_id}: {e}")
            return False
    
    def remove_container(self, container_id: str) -> bool:
        """コンテナ削除"""
        try:
            if container_id in self.containers:
                container = self.containers[container_id]
                container.remove(force=True)
                del self.containers[container_id]
                self.logger.info(f"Removed container: {container_id}")
                return True
            else:
                self.logger.error(f"Container not found: {container_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove container {container_id}: {e}")
            return False
    
    def get_container_status(self, container_id: str) -> Optional[ContainerStatus]:
        """コンテナ状態取得"""
        try:
            if container_id not in self.containers:
                return None
            
            container = self.containers[container_id]
            stats = container.stats(stream=False)
            
            # CPU使用率計算
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # メモリ使用量
            memory_usage = stats['memory_stats']['usage'] / 1024 / 1024  # MB
            
            # ネットワークI/O
            network_io = stats['networks']
            
            # ディスクI/O
            disk_io = stats['blkio_stats']
            
            # 稼働時間
            uptime = time.time() - stats['read']
            
            return ContainerStatus(
                container_id=container_id,
                status=container.status,
                cpu_usage=cpu_percent,
                memory_usage=memory_usage,
                network_io=network_io,
                disk_io=disk_io,
                uptime=uptime
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get container status {container_id}: {e}")
            return None
    
    def list_containers(self) -> List[str]:
        """コンテナ一覧取得"""
        return list(self.containers.keys())
    
    def cleanup_all_containers(self):
        """全コンテナクリーンアップ"""
        for container_id in list(self.containers.keys()):
            try:
                self.stop_container(container_id)
                self.remove_container(container_id)
            except Exception as e:
                self.logger.error(f"Cleanup failed for {container_id}: {e}")
    
    def emergency_stop_all(self):
        """緊急停止（全コンテナ）"""
        self.logger.critical("EMERGENCY STOP: Stopping all containers")
        for container_id in list(self.containers.keys()):
            try:
                container = self.containers[container_id]
                container.kill(signal='SIGKILL')
                self.logger.critical(f"Killed container: {container_id}")
            except Exception as e:
                self.logger.error(f"Failed to kill container {container_id}: {e}")

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # コンテナマネージャー起動
    manager = ContainerManager()
    
    try:
        # サンドボックスコンテナ作成
        container_id = manager.create_sandbox_container()
        print(f"Created container: {container_id}")
        
        # コンテナ開始
        if manager.start_container(container_id):
            print(f"Started container: {container_id}")
            
            # 状態監視
            for i in range(10):
                status = manager.get_container_status(container_id)
                if status:
                    print(f"Status: {status.status}, CPU: {status.cpu_usage:.1f}%, Memory: {status.memory_usage:.1f}MB")
                time.sleep(2)
        
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        manager.cleanup_all_containers()