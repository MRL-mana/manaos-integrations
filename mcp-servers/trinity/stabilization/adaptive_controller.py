#!/usr/bin/env python3
"""
Adaptive Controller - 適応制御システム

システム負荷に応じて処理を自動調整します。
"""

import psutil
from typing import Dict


class AdaptiveController:
    """適応制御システム"""
    
    def __init__(self):
        self.cpu_thresholds = {
            'low': 20,
            'medium': 50,
            'high': 80
        }
        
        self.memory_thresholds = {
            'low': 300,  # MB
            'medium': 500,
            'high': 700
        }
        
        # 現在の制御レベル
        self.current_level = 'medium'
        
        # 各レベルでの設定
        self.level_configs = {
            'low': {
                'max_workers': 6,
                'update_frequency': 5,  # 秒
                'batch_size': 20
            },
            'medium': {
                'max_workers': 4,
                'update_frequency': 10,
                'batch_size': 10
            },
            'high': {
                'max_workers': 2,
                'update_frequency': 30,
                'batch_size': 5
            },
            'critical': {
                'max_workers': 1,
                'update_frequency': 60,
                'batch_size': 1
            }
        }
        
    def adjust(self) -> Dict:
        """システム負荷に応じて調整"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # 負荷レベルを判定
        new_level = self._determine_level(cpu, memory)
        
        if new_level != self.current_level:
            print(f"🔧 Adaptive Controller: {self.current_level} → {new_level}")
            print(f"   CPU: {cpu:.1f}%, Memory: {memory:.0f}MB")
            self.current_level = new_level
            
        config = self.level_configs[self.current_level]
        
        return {
            'level': self.current_level,
            'cpu': cpu,
            'memory': memory,
            'config': config
        }
        
    def _determine_level(self, cpu: float, memory: float) -> str:
        """負荷レベルを判定"""
        if cpu > self.cpu_thresholds['high'] or memory > self.memory_thresholds['high']:
            return 'critical'
        elif cpu > self.cpu_thresholds['medium'] or memory > self.memory_thresholds['medium']:
            return 'high'
        elif cpu < self.cpu_thresholds['low'] and memory < self.memory_thresholds['low']:
            return 'low'
        else:
            return 'medium'
            
    def get_config(self) -> Dict:
        """現在の設定を取得"""
        return self.level_configs[self.current_level]


if __name__ == '__main__':
    controller = AdaptiveController()
    result = controller.adjust()
    print(f"\nCurrent Level: {result['level']}")
    print(f"Config: {result['config']}")
