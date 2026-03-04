#!/usr/bin/env python3
"""
🧠 ManaSpec Auto Proposal AI
AI Learningから自動的に次の仕様を提案する「自己成長AI」

Minaの学習データを分析して、Remiが自発的にProposalを生成
"""

import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests

class AutoProposalAI:
    """自動Proposal生成AI"""
    
    def __init__(self, ai_learning_db: str = "/root/ai_learning.db"):
        self.db_path = ai_learning_db
        self.remi_url = "http://localhost:9200/api/execute"
        self.manaspec_workflow = "/root/manaspec_workflow_engine.py"
    
    async def analyze_patterns(self) -> List[Dict]:
        """パターン分析して改善提案を抽出"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用頻度の高いパターンを取得
        cursor.execute("""
            SELECT pattern_type, pattern_name, pattern_content, usage_count, success_rate, tags
            FROM spec_patterns
            WHERE usage_count >= 1
            ORDER BY usage_count DESC, success_rate DESC
            LIMIT 20
        """)
        
        patterns = []
        for row in cursor.fetchall():
            p_type, p_name, p_content, usage, success_rate, tags = row
            patterns.append({
                "type": p_type,
                "name": p_name,
                "content": p_content,
                "usage_count": usage,
                "success_rate": success_rate,
                "tags": json.loads(tags) if tags else []
            })
        
        conn.close()
        return patterns
    
    async def analyze_archives(self) -> List[Dict]:
        """アーカイブを分析して傾向を抽出"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近のアーカイブを分析
        cursor.execute("""
            SELECT change_id, feature_description, specs, success_metrics
            FROM openspec_archives
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        archives = []
        for row in cursor.fetchall():
            change_id, feature, specs, metrics = row
            archives.append({
                "change_id": change_id,
                "feature": feature,
                "specs": json.loads(specs) if specs else [],
                "metrics": json.loads(metrics) if metrics else {}
            })
        
        conn.close()
        return archives
    
    async def detect_improvement_opportunities(self) -> List[Dict]:
        """改善機会を自動検出"""
        opportunities = []
        
        patterns = await self.analyze_patterns()
        archives = await self.analyze_archives()
        
        # パターンベースの提案
        if patterns:
            # 使用頻度の高いパターンの最適化提案
            top_pattern = patterns[0]
            if top_pattern["usage_count"] >= 2:
                opportunities.append({
                    "type": "pattern_optimization",
                    "priority": "high",
                    "title": f"{top_pattern['name']}の最適化",
                    "description": f"使用回数{top_pattern['usage_count']}回のパターンを最適化する機会があります",
                    "suggested_action": "共通化・抽象化の検討"
                })
        
        # アーカイブベースの提案
        if len(archives) >= 3:
            # 類似機能の統合提案
            opportunities.append({
                "type": "feature_consolidation",
                "priority": "medium",
                "title": "関連機能の統合検討",
                "description": f"過去{len(archives)}件のアーカイブから、統合可能な機能を検出",
                "suggested_action": "機能の整理・リファクタリング"
            })
        
        # 成功率ベースの提案
        for pattern in patterns:
            if pattern["success_rate"] < 0.8:
                opportunities.append({
                    "type": "quality_improvement",
                    "priority": "high",
                    "title": f"{pattern['name']}の品質改善",
                    "description": f"成功率{pattern['success_rate']*100:.0f}%のパターンを改善",
                    "suggested_action": "実装方法の見直し"
                })
        
        return opportunities
    
    async def generate_auto_proposal(self, opportunity: Dict) -> Optional[str]:
        """検出した機会から自動的にProposalを生成"""
        print("\n🧠 自動Proposal生成開始...")
        print(f"タイプ: {opportunity['type']}")
        print(f"タイトル: {opportunity['title']}")
        
        # Remiに提案生成を依頼
        remi_prompt = f"""
AI Learning Systemの分析結果から、以下の改善提案を検出しました：

【タイトル】{opportunity['title']}
【説明】{opportunity['description']}
【推奨アクション】{opportunity['suggested_action']}
【優先度】{opportunity['priority']}

このための OpenSpec Proposal を生成してください。
change-id、requirements、scenarios、implementation tasksを含めてください。
"""
        
        try:
            response = requests.post(
                self.remi_url,
                json={
                    "text": remi_prompt,
                    "actor": "remi",
                    "source": "auto_proposal_ai"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                remi_proposal = result.get("result", "")
                
                print("✅ Remiから提案取得")
                print(f"\n{'='*60}")
                print(remi_proposal[:500] + "..." if len(remi_proposal) > 500 else remi_proposal)
                print(f"{'='*60}\n")
                
                # change-idを生成
                change_id = self._generate_change_id(opportunity['title'])
                
                return change_id
            else:
                print("⚠️ Remi offline - template使用")
                return None
        except Exception as e:
            print(f"❌ Proposal生成エラー: {e}")
            return None
    
    def _generate_change_id(self, title: str) -> str:
        """タイトルからchange-idを生成"""
        import re
        words = re.findall(r'\w+', title.lower())
        if words and words[0] not in ['add', 'update', 'remove', 'refactor', 'optimize']:
            words.insert(0, 'optimize')
        return '-'.join(words[:5])
    
    async def auto_suggest_loop(self, interval_hours: int = 24):
        """定期的に改善提案を自動生成"""
        print(f"🔄 自動提案ループ開始（{interval_hours}時間ごと）")
        
        while True:
            print(f"\n{'='*60}")
            print(f"🧠 自動分析実行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
            # 改善機会を検出
            opportunities = await self.detect_improvement_opportunities()
            
            if opportunities:
                print(f"✨ {len(opportunities)}件の改善機会を検出！\n")
                
                for opp in opportunities:
                    print(f"【{opp['priority'].upper()}】{opp['title']}")
                    print(f"  {opp['description']}")
                    print(f"  推奨: {opp['suggested_action']}\n")
                    
                    # 高優先度のみ自動生成
                    if opp['priority'] == 'high':
                        change_id = await self.generate_auto_proposal(opp)
                        if change_id:
                            print(f"✅ 自動Proposal作成: {change_id}")
            else:
                print("✓ 現時点で改善提案なし")
            
            # 次回まで待機
            await asyncio.sleep(interval_hours * 3600)
    
    async def analyze_obsidian_notes(self, vault_path: str = "/root/obsidian_vault") -> List[Dict]:
        """Obsidianノートを解析して新機能のヒントを抽出"""
        vault = Path(vault_path)
        suggestions = []
        
        # ManaSpecフォルダ以外のノートを分析
        for note_file in vault.rglob("*.md"):
            # ManaSpecフォルダは除外
            if "ManaSpec" in str(note_file):
                continue
            
            content = note_file.read_text()
            
            # TODOやアイデアを検出
            import re
            todos = re.findall(r'- \[ \] (.+)', content)
            ideas = re.findall(r'(?:アイデア|idea|TODO)[:：](.+)', content, re.IGNORECASE)
            
            if todos or ideas:
                suggestions.append({
                    "source": str(note_file.relative_to(vault)),
                    "todos": todos[:5],
                    "ideas": ideas[:5]
                })
        
        return suggestions
    
    async def generate_from_obsidian(self, vault_path: str = "/root/obsidian_vault"):
        """Obsidianノートから自動的にProposal生成"""
        print(f"\n📝 Obsidian分析開始: {vault_path}\n")
        
        suggestions = await self.analyze_obsidian_notes(vault_path)
        
        if suggestions:
            print(f"✨ {len(suggestions)}個のノートからヒント発見！\n")
            
            for suggestion in suggestions[:3]:  # 上位3件
                print(f"📄 {suggestion['source']}")
                if suggestion['todos']:
                    print(f"  TODOs: {len(suggestion['todos'])}件")
                if suggestion['ideas']:
                    print(f"  Ideas: {len(suggestion['ideas'])}件")
                print()
                
                # Remiに提案生成を依頼
                if suggestion['todos']:
                    feature = suggestion['todos'][0]
                    print(f"  → Proposalを生成: {feature}")
                    
                    opportunity = {
                        "type": "obsidian_suggestion",
                        "priority": "medium",
                        "title": feature,
                        "description": f"Obsidianノート（{suggestion['source']}）から抽出",
                        "suggested_action": "実装検討"
                    }
                    
                    change_id = await self.generate_auto_proposal(opportunity)
                    if change_id:
                        print(f"  ✅ 自動Proposal作成: {change_id}\n")
        else:
            print("ℹ️ Obsidianノートから提案なし")


async def main():
    """デモ実行"""
    ai = AutoProposalAI()
    
    print("🧠 ManaSpec Auto Proposal AI\n")
    print("="*60)
    print("自己成長フェーズ - AIが自発的に改善提案を生成")
    print("="*60 + "\n")
    
    # 1. パターン分析
    print("📊 Phase 1: パターン分析\n")
    patterns = await ai.analyze_patterns()
    print(f"検出されたパターン: {len(patterns)}件")
    for pattern in patterns[:3]:
        print(f"  • {pattern['name']}: 使用{pattern['usage_count']}回, 成功率{pattern['success_rate']*100:.0f}%")
    print()
    
    # 2. 改善機会検出
    print("🔍 Phase 2: 改善機会検出\n")
    opportunities = await ai.detect_improvement_opportunities()
    print(f"改善機会: {len(opportunities)}件\n")
    for opp in opportunities:
        print(f"【{opp['priority'].upper()}】{opp['title']}")
        print(f"  {opp['description']}")
        print(f"  推奨: {opp['suggested_action']}\n")
    
    # 3. Obsidian分析
    print("📝 Phase 3: Obsidian分析\n")
    await ai.generate_from_obsidian()
    
    print("\n" + "="*60)
    print("✅ 自動提案AI - デモ完了")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())

