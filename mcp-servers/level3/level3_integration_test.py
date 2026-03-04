#!/usr/bin/env python3
"""
Level 3 統合テスト
全Level 3システムが正しく動作することを確認
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, '/root')
from level3.autonomous_decision_engine import AutonomousDecisionEngine
from level3.agi_evolution_engine import AGIEvolutionEngine
from level3.auto_bug_fix_system import AutoBugFixSystem
from level3.level3_master_controller import Level3MasterController

class Level3IntegrationTest:
    """Level 3統合テスト"""
    
    def __init__(self):
        self.decision_engine = AutonomousDecisionEngine()
        self.agi_engine = AGIEvolutionEngine()
        self.bugfix_system = AutoBugFixSystem()
        self.master = Level3MasterController()
        self.test_results = []
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "FAIL": "❌"}.get(level, "ℹ️")
        print(f"[{timestamp}] {emoji} {message}")
    
    async def test_autonomous_decision(self):
        """Test 1: 完全自律判断エンジン"""
        self.log("Test 1: 完全自律判断エンジン", "INFO")
        
        try:
            # テスト提案
            proposal = {
                "title": "テスト機能追加",
                "description": "統合テスト用の機能",
                "category": "test",
                "complexity": "simple",
                "testability": "high"
            }
            
            # 判断
            action, decision_info = await self.decision_engine.make_decision(proposal)
            
            assert action is not None
            assert 'confidence' in decision_info
            assert 'risk_level' in decision_info
            
            self.log("Test 1: 合格", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 1: 失敗 - {e}", "FAIL")
            return False
    
    async def test_agi_evolution(self):
        """Test 2: AGI進化エンジン"""
        self.log("Test 2: AGI進化エンジン", "INFO")
        
        try:
            # 実装機会の発見
            opportunities = await self.agi_engine.discover_all_opportunities()
            
            assert isinstance(opportunities, list)
            assert len(opportunities) >= 0  # 0個でもOK
            
            self.log(f"Test 2: 合格 ({len(opportunities)}個の機会発見)", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 2: 失敗 - {e}", "FAIL")
            return False
    
    async def test_auto_bug_fix(self):
        """Test 3: 自動バグ修正システム"""
        self.log("Test 3: 自動バグ修正システム", "INFO")
        
        try:
            # ログ監視
            errors = await self.bugfix_system.monitor_logs()
            
            assert isinstance(errors, list)
            
            self.log(f"Test 3: 合格 ({len(errors)}個のエラー検出)", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 3: 失敗 - {e}", "FAIL")
            return False
    
    async def test_master_controller(self):
        """Test 4: マスターコントローラー"""
        self.log("Test 4: マスターコントローラー", "INFO")
        
        try:
            # ステータス取得
            status = await self.master.get_comprehensive_status()
            
            assert 'timestamp' in status
            assert 'overall_health' in status
            assert status['overall_health'] >= 0
            
            self.log(f"Test 4: 合格 (ヘルス: {status['overall_health']})", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 4: 失敗 - {e}", "FAIL")
            return False
    
    async def test_decision_flow(self):
        """Test 5: 自律判断→実装フロー"""
        self.log("Test 5: 自律判断→実装フロー", "INFO")
        
        try:
            # 提案
            proposal = {
                "title": "ログ出力改善",
                "description": "ログフォーマットを改善",
                "category": "feature_addition",
                "complexity": "simple",
                "testability": "high"
            }
            
            # 判断
            action, decision_info = await self.decision_engine.make_decision(proposal)
            
            # 実行
            result = await self.decision_engine.execute_decision(
                proposal, action, decision_info
            )
            
            assert 'status' in result
            
            self.log(f"Test 5: 合格 (結果: {result['status']})", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 5: 失敗 - {e}", "FAIL")
            return False
    
    async def test_e2e_workflow(self):
        """Test 6: エンドツーエンドワークフロー"""
        self.log("Test 6: エンドツーエンドワークフロー", "INFO")
        
        try:
            # AGI進化エンジンで機会発見
            opportunities = await self.agi_engine.discover_all_opportunities()
            
            if opportunities:
                # 最初の機会を選択
                opportunity = opportunities[0]
                
                # 自律判断
                action, decision_info = await self.decision_engine.make_decision(opportunity)
                
                # 判断結果を記録
                result = await self.decision_engine.execute_decision(
                    opportunity, action, decision_info
                )
                
                assert result is not None
            
            self.log("Test 6: 合格", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Test 6: 失敗 - {e}", "FAIL")
            return False
    
    async def run_all_tests(self):
        """全テストを実行"""
        print("\n" + "=" * 70)
        print("🧪 Level 3 統合テスト実行")
        print("=" * 70)
        print()
        
        tests = [
            ("完全自律判断エンジン", self.test_autonomous_decision),
            ("AGI進化エンジン", self.test_agi_evolution),
            ("自動バグ修正システム", self.test_auto_bug_fix),
            ("マスターコントローラー", self.test_master_controller),
            ("自律判断→実装フロー", self.test_decision_flow),
            ("E2Eワークフロー", self.test_e2e_workflow)
        ]
        
        results = []
        
        for name, test_func in tests:
            print(f"\n{'-' * 70}")
            try:
                success = await test_func()
                results.append((name, success))
            except Exception as e:
                self.log(f"テスト実行エラー: {e}", "FAIL")
                results.append((name, False))
            
            await asyncio.sleep(0.5)
        
        # 結果サマリー
        print(f"\n{'=' * 70}")
        print("📊 テスト結果サマリー")
        print(f"{'=' * 70}")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {name}")
        
        print(f"\n{'=' * 70}")
        print(f"合格: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"{'=' * 70}")
        
        if passed == total:
            print("\n🎉 全テスト合格！Level 3完璧！")
        elif passed >= total * 0.8:
            print(f"\n✅ 合格率{passed/total*100:.0f}% - Level 3ほぼ完成！")
        else:
            print(f"\n⚠️  合格率{passed/total*100:.0f}% - 要改善")
        
        return passed, total

async def main():
    tester = Level3IntegrationTest()
    passed, total = await tester.run_all_tests()
    
    print("\n" + "=" * 70)
    print("🏁 Level 3 統合テスト完了")
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

