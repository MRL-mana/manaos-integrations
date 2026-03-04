#!/usr/bin/env python3
"""
⚡ ManaOS Process Consolidator
234個のAI関連プロセスを統合・最適化するシステム

機能:
- 重複プロセスの検出と統合
- シングルトンパターンの自動実装
- プロセスプーリング
- リソース最適化
"""

import os
import json
import psutil
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessConsolidator:
    """プロセス統合クラス"""
    
    def __init__(self):
        self.processes = []
        self.consolidation_plan = {}
        
    def analyze_processes(self) -> Dict[str, Any]:
        """プロセス分析"""
        logger.info("🔍 プロセス分析開始...")
        
        process_groups = defaultdict(list)
        total_memory = 0
        total_cpu = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                info = proc.info
                cmdline = ' '.join(info['cmdline'] or [])
                
                # AI関連プロセス
                if any(keyword in cmdline.lower() for keyword in 
                       ['python', 'trinity', 'mana', 'ai', 'ml', 'torch']):
                    
                    # スクリプト名で分類
                    script = self._extract_script_name(cmdline)
                    if script:
                        process_groups[script].append({
                            'pid': info['pid'],
                            'cpu': info['cpu_percent'] or 0,
                            'memory_mb': info['memory_info'].rss / (1024**2) if info['memory_info'] else 0
                        })
                        total_memory += info['memory_info'].rss / (1024**2) if info['memory_info'] else 0
                        total_cpu += info['cpu_percent'] or 0
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 統合候補を特定
        consolidation_candidates = []
        for script, procs in process_groups.items():
            if len(procs) > 1:
                total_mem = sum(p['memory_mb'] for p in procs)
                consolidation_candidates.append({
                    'script': script,
                    'instances': len(procs),
                    'total_memory_mb': total_mem,
                    'pids': [p['pid'] for p in procs],
                    'potential_savings_mb': total_mem * 0.7  # 70%削減見込み
                })
        
        # 優先度順にソート
        consolidation_candidates.sort(key=lambda x: x['potential_savings_mb'], reverse=True)
        
        return {
            'total_processes': len([p for procs in process_groups.values() for p in procs]),
            'unique_scripts': len(process_groups),
            'duplicate_scripts': len(consolidation_candidates),
            'total_memory_mb': total_memory,
            'consolidation_candidates': consolidation_candidates[:10],
            'potential_savings_mb': sum(c['potential_savings_mb'] for c in consolidation_candidates)
        }
    
    def _extract_script_name(self, cmdline: str) -> str:
        """スクリプト名抽出"""
        parts = cmdline.split()
        for part in parts:
            if part.endswith('.py'):
                return os.path.basename(part)
        return ""
    
    def generate_consolidation_plan(self, analysis: Dict) -> Dict:
        """統合プランを生成"""
        logger.info("📋 統合プラン生成中...")
        
        plan = {
            'timestamp': datetime.now().isoformat(),
            'actions': [],
            'estimated_savings': {
                'memory_mb': analysis['potential_savings_mb'],
                'processes': sum(c['instances'] - 1 for c in analysis['consolidation_candidates'])
            }
        }
        
        for candidate in analysis['consolidation_candidates']:
            action = {
                'script': candidate['script'],
                'current_instances': candidate['instances'],
                'target_instances': 1,
                'action': 'consolidate',
                'method': self._determine_consolidation_method(candidate),
                'priority': 'high' if candidate['potential_savings_mb'] > 100 else 'medium'
            }
            plan['actions'].append(action)
        
        return plan
    
    def _determine_consolidation_method(self, candidate: Dict) -> str:
        """統合方法を決定"""
        script = candidate['script']
        
        if 'turbo' in script.lower() or 'enhancer' in script.lower():
            return 'singleton_pattern'
        elif 'main.py' in script:
            return 'process_pooling'
        else:
            return 'instance_limit'
    
    def create_singleton_wrapper(self, script_name: str) -> str:
        """シングルトンラッパーを生成"""
        wrapper_code = f"""#!/usr/bin/env python3
\"\"\"
Singleton Wrapper for {script_name}
自動生成されたシングルトンパターン実装
\"\"\"

import os
import sys
import fcntl
import atexit

LOCK_FILE = '/tmp/{script_name}.lock'

def acquire_lock():
    \"\"\"ロックファイルを取得（既に実行中なら終了）\"\"\"
    global lock_file
    lock_file = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        atexit.register(release_lock)
        return True
    except IOError:
        print(f"{{script_name}} は既に実行中です。", file=sys.stderr)
        return False

def release_lock():
    \"\"\"ロックファイルを解放\"\"\"
    try:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except IOError as e:
        pass

if __name__ == "__main__":
    if not acquire_lock():
        sys.exit(1)
    
    # オリジナルのスクリプトをインポート・実行
    original_script = "/root/{script_name}"
    with open(original_script) as f:
        code = compile(f.read(), original_script, 'exec')
        exec(code)
"""
        return wrapper_code
    
    def execute_consolidation(self, plan: Dict, dry_run: bool = True) -> Dict:
        """統合を実行"""
        logger.info("⚡ 統合実行中...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'actions_taken': [],
            'errors': []
        }
        
        for action in plan['actions'][:3]:  # 最初の3つを実行
            script = action['script']
            method = action['method']
            
            if dry_run:
                logger.info(f"  [DRY RUN] {script}: {method}")
                results['actions_taken'].append({
                    'script': script,
                    'method': method,
                    'status': 'planned'
                })
            else:
                try:
                    if method == 'singleton_pattern':
                        wrapper = self.create_singleton_wrapper(script)
                        wrapper_path = f"/root/wrappers/singleton_{script}"
                        os.makedirs("/root/wrappers", exist_ok=True)
                        with open(wrapper_path, 'w') as f:
                            f.write(wrapper)
                        os.chmod(wrapper_path, 0o755)
                        
                        results['actions_taken'].append({
                            'script': script,
                            'method': method,
                            'status': 'wrapper_created',
                            'wrapper_path': wrapper_path
                        })
                    
                    logger.info(f"  ✅ {script}: {method} 適用完了")
                    
                except Exception as e:
                    logger.error(f"  ❌ {script}: {e}")
                    results['errors'].append({
                        'script': script,
                        'error': str(e)
                    })
        
        return results

def main():
    """メイン実行"""
    print("⚡ ManaOS Process Consolidator")
    print("="*80)
    
    consolidator = ProcessConsolidator()
    
    # 分析
    print("\n🔍 プロセス分析中...")
    analysis = consolidator.analyze_processes()
    
    print("\n📊 分析結果:")
    print(f"  総プロセス数: {analysis['total_processes']}")
    print(f"  ユニークスクリプト: {analysis['unique_scripts']}")
    print(f"  重複スクリプト: {analysis['duplicate_scripts']}")
    print(f"  総メモリ使用: {analysis['total_memory_mb']:.1f} MB")
    
    print("\n💡 統合候補 (Top 5):")
    for i, candidate in enumerate(analysis['consolidation_candidates'][:5], 1):
        print(f"  {i}. {candidate['script']}")
        print(f"     インスタンス: {candidate['instances']}個")
        print(f"     メモリ削減見込: {candidate['potential_savings_mb']:.1f} MB")
    
    # 統合プラン生成
    print("\n📋 統合プラン生成中...")
    plan = consolidator.generate_consolidation_plan(analysis)
    
    print("\n🎯 予想効果:")
    print(f"  メモリ削減: {plan['estimated_savings']['memory_mb']:.1f} MB")
    print(f"  プロセス削減: {plan['estimated_savings']['processes']} 個")
    
    # ドライランで実行
    print("\n⚡ 統合実行 (DRY RUN)...")
    results = consolidator.execute_consolidation(plan, dry_run=True)
    
    print("\n✅ 完了！")
    print(f"  計画されたアクション: {len(results['actions_taken'])}")
    
    # レポート保存
    report = {
        'analysis': analysis,
        'plan': plan,
        'results': results
    }
    
    report_file = f"/root/logs/process_consolidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 レポート: {report_file}")
    print("="*80)

if __name__ == "__main__":
    main()








