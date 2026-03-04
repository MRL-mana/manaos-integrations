#!/usr/bin/env python3
"""
自動バグ修正システム - Level 3
エラー検出から5分以内に自動修正
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

sys.path.insert(0, '/root')
from level3.autonomous_decision_engine import AutonomousDecisionEngine
from mcp_integration_hub import MCPIntegrationHub

class AutoBugFixSystem:
    """自動バグ修正システム"""
    
    def __init__(self):
        self.decision_engine = AutonomousDecisionEngine()
        self.hub = MCPIntegrationHub()
        self.fix_log = Path("/root/level3/bug_fix_log.json")
        self.monitored_logs = [
            "/root/logs/mcp_integration_hub.log",
            "/root/logs/github_webhook.log",
            "/root/logs/x280_sync.log",
            "/root/logs/self_learning.log"
        ]
        self.ensure_log()
    
    def ensure_log(self):
        """ログファイル初期化"""
        if not self.fix_log.exists():
            with open(self.fix_log, 'w') as f:
                json.dump({
                    "fixes": [],
                    "stats": {
                        "total_errors": 0,
                        "auto_fixed": 0,
                        "manual_required": 0,
                        "average_fix_time": 0
                    }
                }, f, indent=2)
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "FIX": "🔧",
            "DETECT": "🔍"
        }.get(level, "ℹ️")
        print(f"[{timestamp}] {emoji} {message}")
    
    async def monitor_logs(self) -> List[Dict]:
        """ログファイルを監視してエラーを検出"""
        errors = []
        
        for log_file in self.monitored_logs:
            log_path = Path(log_file)
            if not log_path.exists():
                continue
            
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    
                    # 最新100行のみチェック
                    recent_lines = lines[-100:]
                    
                    for line in recent_lines:
                        # エラーパターン検出
                        if any(pattern in line.lower() for pattern in ['error', 'exception', 'failed', 'traceback']):
                            error = self._parse_error(line, log_file)
                            if error:
                                errors.append(error)
            except:
                pass
        
        # 重複除去
        unique_errors = []
        seen = set()
        for error in errors:
            key = f"{error['type']}_{error['message']}"
            if key not in seen:
                seen.add(key)
                unique_errors.append(error)
        
        return unique_errors
    
    def _parse_error(self, line: str, log_file: str) -> Optional[Dict]:
        """エラー行をパース"""
        # 簡易的なエラー解析
        error_patterns = {
            'ImportError': r'ImportError: (.+)',
            'FileNotFoundError': r'FileNotFoundError: (.+)',
            'KeyError': r'KeyError: (.+)',
            'TypeError': r'TypeError: (.+)',
            'ValueError': r'ValueError: (.+)',
            'ConnectionError': r'ConnectionError: (.+)',
            'TimeoutError': r'TimeoutError: (.+)'
        }
        
        for error_type, pattern in error_patterns.items():
            match = re.search(pattern, line)
            if match:
                return {
                    "type": error_type,
                    "message": match.group(1).strip(),
                    "log_file": log_file,
                    "timestamp": datetime.now().isoformat(),
                    "line": line.strip()
                }
        
        # 一般的なエラー
        if 'error' in line.lower():
            return {
                "type": "GeneralError",
                "message": line.strip()[:200],
                "log_file": log_file,
                "timestamp": datetime.now().isoformat(),
                "line": line.strip()
            }
        
        return None
    
    async def search_similar_bugs(self, error: Dict) -> List[Dict]:
        """類似バグを検索"""
        self.log(f"類似バグ検索: {error['type']}", "DETECT")
        
        # AI Learning MCPで類似パターン検索
        patterns = await self.hub.ai_search_patterns(
            query=error['message'],
            limit=10
        )
        
        similar = [
            p for p in patterns['patterns']
            if 'bug' in p.get('type', '').lower() or
               'fix' in p.get('type', '').lower() or
               'error' in p.get('pattern', '').lower()
        ]
        
        self.log(f"類似バグ: {len(similar)}件発見", "DETECT")
        
        return similar
    
    async def generate_fix(self, error: Dict, similar_bugs: List[Dict]) -> Dict:
        """修正案を生成"""
        self.log("修正案生成中...", "FIX")
        
        fix_proposal = {
            "title": f"{error['type']}の自動修正",
            "description": f"エラー: {error['message']}\n\n修正: ",
            "category": "bug_fix",
            "complexity": "simple",
            "testability": "high",
            "error": error,
            "similar_bugs": similar_bugs
        }
        
        # エラータイプ別の修正戦略
        if error['type'] == 'ImportError':
            fix_proposal['description'] += "必要なモジュールをインポートまたはインストール"
            fix_proposal['fix_strategy'] = "add_import"
        
        elif error['type'] == 'FileNotFoundError':
            fix_proposal['description'] += "ファイル/ディレクトリを作成またはパス修正"
            fix_proposal['fix_strategy'] = "create_file_or_fix_path"
        
        elif error['type'] == 'KeyError':
            fix_proposal['description'] += "辞書キーの存在チェックを追加"
            fix_proposal['fix_strategy'] = "add_key_check"
        
        elif error['type'] == 'TypeError':
            fix_proposal['description'] += "型変換またはnullチェックを追加"
            fix_proposal['fix_strategy'] = "add_type_check"
        
        elif error['type'] == 'ConnectionError':
            fix_proposal['description'] += "リトライロジックまたはタイムアウト処理を追加"
            fix_proposal['fix_strategy'] = "add_retry_logic"
        
        else:
            fix_proposal['description'] += "エラーハンドリングを追加"
            fix_proposal['fix_strategy'] = "add_error_handling"
        
        return fix_proposal
    
    async def apply_fix(self, fix_proposal: Dict) -> Dict:
        """修正を適用"""
        self.log("修正適用中...", "FIX")
        
        # 自律判断エンジンで判断
        action, decision_info = await self.decision_engine.make_decision(fix_proposal)
        
        # 実行
        result = await self.decision_engine.execute_decision(
            fix_proposal, action, decision_info
        )
        
        return result
    
    async def fix_bug(self, error: Dict) -> Dict:
        """1つのバグを修正"""
        self.log(f"バグ修正開始: {error['type']}", "FIX")
        
        fix_start = datetime.now()
        
        # 類似バグ検索
        similar_bugs = await self.search_similar_bugs(error)
        
        # 修正案生成
        fix_proposal = await self.generate_fix(error, similar_bugs)
        
        # 修正適用
        result = await self.apply_fix(fix_proposal)
        
        fix_end = datetime.now()
        fix_duration = (fix_end - fix_start).total_seconds()
        
        fix_result = {
            "error": error,
            "fix_proposal": fix_proposal,
            "result": result,
            "fix_duration": fix_duration,
            "timestamp": fix_start.isoformat()
        }
        
        # ログに記録
        await self._record_fix(fix_result)
        
        if result['status'] == 'completed':
            self.log(f"バグ修正完了: {fix_duration:.1f}秒", "SUCCESS")
        else:
            self.log("バグ修正失敗または承認待ち", "ERROR")
        
        return fix_result
    
    async def _record_fix(self, fix_result: Dict):
        """修正結果を記録"""
        with open(self.fix_log, 'r') as f:
            log_data = json.load(f)
        
        log_data['fixes'].append(fix_result)
        log_data['stats']['total_errors'] += 1
        
        if fix_result['result']['status'] == 'completed':
            log_data['stats']['auto_fixed'] += 1
        else:
            log_data['stats']['manual_required'] += 1
        
        # 平均修正時間更新
        if log_data['stats']['auto_fixed'] > 0:
            total_time = sum(
                f['fix_duration'] for f in log_data['fixes']
                if f['result']['status'] == 'completed'
            )
            log_data['stats']['average_fix_time'] = total_time / log_data['stats']['auto_fixed']
        
        with open(self.fix_log, 'w') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    async def continuous_monitoring(self, check_interval: int = 60):
        """継続的監視（60秒ごと）"""
        self.log("🔍 継続的エラー監視開始", "INFO")
        self.log(f"チェック間隔: {check_interval}秒", "INFO")
        
        try:
            while True:
                # ログ監視
                errors = await self.monitor_logs()
                
                if errors:
                    self.log(f"\n{len(errors)}個の新しいエラーを検出", "DETECT")
                    
                    # 各エラーを修正
                    for error in errors[:5]:  # 最大5個まで
                        await self.fix_bug(error)
                        await asyncio.sleep(1)
                
                await asyncio.sleep(check_interval)
        
        except KeyboardInterrupt:
            self.log("\n継続的監視を停止しました", "INFO")
        except Exception as e:
            self.log(f"\nエラーが発生しました: {e}", "ERROR")
    
    async def get_fix_stats(self) -> Dict:
        """修正統計取得"""
        with open(self.fix_log, 'r') as f:
            log_data = json.load(f)
        
        return log_data['stats']

async def main():
    print("\n" + "=" * 70)
    print("🔧 自動バグ修正システム - Level 3")
    print("=" * 70)
    
    system = AutoBugFixSystem()
    
    # デモ: ログ監視＆バグ修正
    print("\n1️⃣ ログ監視実行")
    errors = await system.monitor_logs()
    
    if errors:
        print(f"検出エラー: {len(errors)}個")
        
        for error in errors[:3]:  # 最大3個まで
            print(f"\n{'-' * 70}")
            await system.fix_bug(error)
            await asyncio.sleep(1)
    else:
        print("エラーは検出されませんでした")
    
    # 統計表示
    print(f"\n{'=' * 70}")
    print("📊 修正統計")
    print(f"{'=' * 70}")
    
    stats = await system.get_fix_stats()
    print(f"総エラー数: {stats['total_errors']}")
    print(f"自動修正: {stats['auto_fixed']}")
    print(f"手動必要: {stats['manual_required']}")
    if stats['auto_fixed'] > 0:
        print(f"平均修正時間: {stats['average_fix_time']:.1f}秒")
    
    print(f"\n{'=' * 70}")
    print("🎉 完了")
    print(f"{'=' * 70}")
    print(f"\n修正ログ: {system.fix_log}")
    print("\n💡 使い方:")
    print("  # 継続監視（60秒ごと）")
    print("  python3 /root/level3/auto_bug_fix_system.py continuous")
    print("")
    print("  # バックグラウンドで実行")
    print("  nohup python3 /root/level3/auto_bug_fix_system.py continuous > /root/logs/auto_bug_fix.log 2>&1 &")

if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    
    if mode == "continuous":
        asyncio.run(AutoBugFixSystem().continuous_monitoring())
    else:
        asyncio.run(main())

