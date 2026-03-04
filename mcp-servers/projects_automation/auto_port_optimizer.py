#!/usr/bin/env python3
"""
自動ポート転送最適化スクリプト
ハイブリッドモードで効率的にポート転送を管理
"""

import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class PortOptimizer:
    def __init__(self):
        self.important_ports = {
            # 必須サービス
            22: "SSH",
            80: "HTTP", 
            443: "HTTPS",
            3000: "Web Dev",
            8000: "Web Server",
            8080: "Alt Web",
            
            # データベース
            5432: "PostgreSQL",
            5433: "PostgreSQL Alt",
            6379: "Redis",
            6380: "Redis Alt",
            
            # 開発ツール
            8888: "Jupyter",
            8889: "Jupyter Alt",
            8891: "Jupyter Alt2",
            3002: "React Dev",
            
            # 監視
            9000: "Prometheus",
            9090: "Grafana",
            9200: "Elasticsearch",
            
            # その他重要
            5900: "VNC",
            11434: "Ollama"
        }
        
        self.auto_ports = set()
        self.process_ports = {}
        
    def get_listening_ports(self) -> List[Tuple[int, str, str]]:
        """リスニングポート一覧を取得"""
        try:
            result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True)
            ports = []
            
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        addr = parts[3]
                        if ':' in addr:
                            port = int(addr.split(':')[-1])
                            protocol = parts[0]
                            ports.append((port, protocol, addr))
            
            return ports
        except Exception as e:
            print(f"ポート取得エラー: {e}")
            return []
    
    def get_process_info(self, port: int) -> Dict:
        """ポートを使用しているプロセス情報を取得"""
        try:
            result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')[1:]  # ヘッダーをスキップ
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        return {
                            'pid': parts[1],
                            'process': parts[0],
                            'user': parts[2] if len(parts) > 2 else 'unknown'
                        }
        except Exception as e:
            print(f"プロセス情報取得エラー (ポート{port}): {e}")
        
        return {'pid': 'unknown', 'process': 'unknown', 'user': 'unknown'}
    
    def categorize_ports(self, ports: List[Tuple[int, str, str]]) -> Dict[str, List[int]]:
        """ポートをカテゴリ別に分類"""
        categories = {
            'important': [],
            'development': [],
            'monitoring': [],
            'database': [],
            'unknown': []
        }
        
        for port, protocol, addr in ports:
            if port in self.important_ports:
                if port in [22, 80, 443, 3000, 8000, 8080]:
                    categories['important'].append(port)
                elif port in [5432, 5433, 6379, 6380]:
                    categories['database'].append(port)
                elif port in [9000, 9090, 9200]:
                    categories['monitoring'].append(port)
                else:
                    categories['development'].append(port)
            else:
                # ポート範囲で推測
                if 5000 <= port <= 5999:
                    categories['development'].append(port)
                elif 9000 <= port <= 9999:
                    categories['monitoring'].append(port)
                elif 8000 <= port <= 8999:
                    categories['development'].append(port)
                else:
                    categories['unknown'].append(port)
        
        return categories
    
    def generate_optimization_plan(self, categories: Dict[str, List[int]]) -> Dict:
        """最適化プランを生成"""
        plan = {
            'keep_essential': [],
            'keep_development': [],
            'keep_monitoring': [],
            'auto_manage': [],
            'stop_unnecessary': [],
            'manual_review': []
        }
        
        # 必須ポートは必ず保持
        plan['keep_essential'] = categories['important'] + categories['database']
        
        # 開発ポート（上位10個まで）
        dev_ports = sorted(categories['development'], reverse=True)[:10]
        plan['keep_development'] = dev_ports
        
        # 監視ポート（上位5個まで）
        mon_ports = sorted(categories['monitoring'], reverse=True)[:5]
        plan['keep_monitoring'] = mon_ports
        
        # 自動管理対象（重要度中）
        plan['auto_manage'] = [p for p in categories['development'][10:20]]
        
        # 停止対象（重要度低）
        plan['stop_unnecessary'] = categories['unknown'][:20]  # 上位20個まで
        
        # 手動確認が必要
        plan['manual_review'] = categories['unknown'][20:]
        
        return plan
    
    def create_port_forwarding_config(self, plan: Dict) -> str:
        """ポート転送設定ファイルを生成"""
        config = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'strategy': 'hybrid_optimized',
            'port_forwarding': {
                'essential': {
                    'ports': plan['keep_essential'],
                    'auto_forward': True,
                    'priority': 'high'
                },
                'development': {
                    'ports': plan['keep_development'],
                    'auto_forward': True,
                    'priority': 'medium'
                },
                'monitoring': {
                    'ports': plan['keep_monitoring'],
                    'auto_forward': True,
                    'priority': 'medium'
                },
                'auto_managed': {
                    'ports': plan['auto_manage'],
                    'auto_forward': False,
                    'priority': 'low',
                    'on_demand': True
                }
            },
            'optimization': {
                'max_auto_ports': 20,
                'hybrid_mode': True,
                'auto_cleanup': True
            }
        }
        
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    def create_management_script(self, plan: Dict) -> str:
        """ポート管理スクリプトを生成"""
        script = f"""#!/bin/bash
# 自動ポート最適化スクリプト
# 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo "🚀 ポート最適化を開始..."

# 必須ポートの確認
echo "📋 必須ポート ({len(plan['keep_essential'])}個):"
for port in {' '.join(map(str, plan['keep_essential']))}; do
    echo "  ✓ ポート $port - 必須サービス"
done

# 開発ポートの確認
echo "🔧 開発ポート ({len(plan['keep_development'])}個):"
for port in {' '.join(map(str, plan['keep_development']))}; do
    echo "  ✓ ポート $port - 開発ツール"
done

# 監視ポートの確認
echo "📊 監視ポート ({len(plan['keep_monitoring'])}個):"
for port in {' '.join(map(str, plan['keep_monitoring']))}; do
    echo "  ✓ ポート $port - 監視ツール"
done

# 自動管理ポート
echo "⚙️ 自動管理ポート ({len(plan['auto_manage'])}個):"
for port in {' '.join(map(str, plan['auto_manage']))}; do
    echo "  ⚡ ポート $port - オンデマンド"
done

# 停止推奨ポート
echo "🛑 停止推奨ポート ({len(plan['stop_unnecessary'])}個):"
for port in {' '.join(map(str, plan['stop_unnecessary']))}; do
    echo "  ⚠️ ポート $port - 停止を検討"
done

echo "✅ 最適化完了！"
echo "📝 設定ファイル: /root/port_forwarding_config.json"
echo "🔧 管理スクリプト: /root/manage_ports.sh"
"""
        return script
    
    def run_optimization(self):
        """最適化を実行"""
        print("🔍 ポート分析を開始...")
        
        # ポート一覧取得
        ports = self.get_listening_ports()
        print(f"📊 検出されたポート数: {len(ports)}")
        
        # カテゴリ分類
        categories = self.categorize_ports(ports)
        print(f"📋 重要ポート: {len(categories['important'])}個")
        print(f"🔧 開発ポート: {len(categories['development'])}個")
        print(f"📊 監視ポート: {len(categories['monitoring'])}個")
        print(f"❓ 不明ポート: {len(categories['unknown'])}個")
        
        # 最適化プラン生成
        plan = self.generate_optimization_plan(categories)
        
        # 設定ファイル生成
        config = self.create_port_forwarding_config(plan)
        with open('/root/port_forwarding_config.json', 'w', encoding='utf-8') as f:
            f.write(config)
        
        # 管理スクリプト生成
        script = self.create_management_script(plan)
        with open('/root/manage_ports.sh', 'w', encoding='utf-8') as f:
            f.write(script)
        
        # 実行権限付与
        os.chmod('/root/manage_ports.sh', 0o755)
        
        print("\n✅ 最適化完了！")
        print("📝 設定ファイル: /root/port_forwarding_config.json")
        print("🔧 管理スクリプト: /root/manage_ports.sh")
        print("📊 最適化結果:")
        print(f"  - 保持ポート: {len(plan['keep_essential']) + len(plan['keep_development']) + len(plan['keep_monitoring'])}個")
        print(f"  - 自動管理: {len(plan['auto_manage'])}個")
        print(f"  - 停止推奨: {len(plan['stop_unnecessary'])}個")
        
        return plan

def main():
    optimizer = PortOptimizer()
    plan = optimizer.run_optimization()
    
    print("\n🎯 次のステップ:")
    print("1. 設定を確認: cat /root/port_forwarding_config.json")
    print("2. 管理スクリプト実行: bash /root/manage_ports.sh")
    print("3. 不要ポート停止: 手動でプロセス停止")

if __name__ == "__main__":
    main()
