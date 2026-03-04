"""
AI Simulator RPG System
自己拡張RPGシステム（Phase 4）

目的: AIが自分の"価値観とスキル"を拡張
- レベル（習熟度）
- スキル（能力タグ）
- 経験値（成功率/失敗率）
- スキルツリー（コード/自動化/推論/対話）
"""

import time
import logging
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

class SkillCategory(Enum):
    """スキルカテゴリー"""
    CODE = "code"                    # コード
    AUTOMATION = "automation"        # 自動化
    REASONING = "reasoning"          # 推論
    COMMUNICATION = "communication"  # 対話
    ANALYSIS = "analysis"            # 分析
    OPTIMIZATION = "optimization"   # 最適化

class SkillLevel(Enum):
    """スキルレベル"""
    BEGINNER = 0    # 初心者
    INTERMEDIATE = 1  # 中級
    ADVANCED = 2    # 上級
    EXPERT = 3      # エキスパート
    MASTER = 4      # マスター

@dataclass
class Skill:
    """スキル"""
    skill_id: str
    name: str
    category: SkillCategory
    level: int = 0  # 0-100
    experience_points: int = 0
    total_uses: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    unlocked_prerequisites: List[str] = field(default_factory=list)
    
    def get_level_name(self) -> str:
        """レベル名称取得"""
        if self.level < 20:
            return "Beginner"
        elif self.level < 40:
            return "Intermediate"
        elif self.level < 60:
            return "Advanced"
        elif self.level < 80:
            return "Expert"
        else:
            return "Master"
    
    def get_success_rate(self) -> float:
        """成功率取得"""
        if self.total_uses == 0:
            return 0.0
        return self.success_count / self.total_uses
    
    def add_experience(self, points: int):
        """経験値追加"""
        self.experience_points += points
        
        # レベルアップ判定
        old_level = self.level
        new_level = self._calculate_level_from_experience()
        self.level = new_level
        
        if new_level > old_level:
            return True  # レベルアップ
        return False
    
    def _calculate_level_from_experience(self) -> int:
        """経験値からレベル計算"""
        # レベル1-100に変換
        if self.experience_points < 100:
            return int(self.experience_points / 10)
        elif self.experience_points < 500:
            return int(10 + (self.experience_points - 100) / 20)
        elif self.experience_points < 1000:
            return int(30 + (self.experience_points - 500) / 25)
        else:
            return min(100, int(50 + (self.experience_points - 1000) / 20))
    
    def record_use(self, success: bool):
        """使用記録"""
        self.total_uses += 1
        self.last_used = time.time()
        
        if success:
            self.success_count += 1
            # 成功時は多めの経験値
            exp_gain = 10 + int(self.get_success_rate() * 10)
            self.add_experience(exp_gain)
        else:
            self.failure_count += 1
            # 失敗時も少々経験値
            exp_gain = 2 + int(self.get_success_rate() * 3)
            self.add_experience(exp_gain)
    
    def can_unlock(self, required_skills: Dict[str, int]) -> bool:
        """アンロック可能かチェック"""
        for skill_id, required_level in required_skills.items():
            # 前提条件のスキルチェックは外部で行う
            pass
        return True

@dataclass
class SkillTreeNode:
    """スキルツリーノード"""
    skill_id: str
    parent_ids: List[str] = field(default_factory=list)
    unlock_condition: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)  # (x, y)
    
@dataclass
class SkillTree:
    """スキルツリー"""
    root_skill_ids: List[str] = field(default_factory=list)
    nodes: Dict[str, SkillTreeNode] = field(default_factory=dict)
    
    def add_node(self, skill_id: str, parent_ids: List[str], 
                 unlock_condition: Dict[str, Any], position: Tuple[int, int]):
        """ノード追加"""
        node = SkillTreeNode(
            skill_id=skill_id,
            parent_ids=parent_ids,
            unlock_condition=unlock_condition,
            position=position
        )
        self.nodes[skill_id] = node
        
        if not parent_ids:
            self.root_skill_ids.append(skill_id)
    
    def get_unlockable_skills(self, skills: Dict[str, Skill]) -> List[str]:
        """アンロック可能なスキル取得"""
        unlockable = []
        
        for skill_id, node in self.nodes.items():
            if skill_id in skills:
                continue  # 既にアンロック済み
            
            # 前提条件チェック
            can_unlock = True
            for parent_id in node.parent_ids:
                if parent_id not in skills:
                    can_unlock = False
                    break
            
            if can_unlock:
                unlockable.append(skill_id)
        
        return unlockable
    
    def get_prerequisite_path(self, skill_id: str) -> List[str]:
        """前提条件チェーン取得"""
        path = []
        visited = set()
        
        def dfs(current_id: str):
            if current_id in visited:
                return
            
            visited.add(current_id)
            
            if current_id in self.nodes:
                node = self.nodes[current_id]
                for parent_id in node.parent_ids:
                    if parent_id not in visited:
                        dfs(parent_id)
                        path.append(parent_id)
        
        dfs(skill_id)
        return path

@dataclass
class CharacterStats:
    """キャラクター統計"""
    total_level: int = 0  # 全スキル平均レベル
    total_experience: int = 0
    unlocked_skill_count: int = 0
    total_task_attempts: int = 0
    total_task_successes: int = 0
    average_success_rate: float = 0.0
    highest_level_skill: Optional[str] = None
    most_used_skill: Optional[str] = None
    specialization: Optional[str] = None
    growth_rate: float = 0.0

class RPGSystem:
    """RPGシステム"""
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_tree = SkillTree()
        self.stats = CharacterStats()
        self.logger = self._setup_logger()
        
        # 初期スキル設定
        self._initialize_base_skills()
        self._build_skill_tree()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('rpg_system')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/rpg_system.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_base_skills(self):
        """ベーススキル初期化"""
        base_skills = [
            {
                'skill_id': 'basic_coding',
                'name': 'Basic Coding',
                'category': SkillCategory.CODE,
                'level': 20,
                'experience_points': 200
            },
            {
                'skill_id': 'automation_basics',
                'name': 'Automation Basics',
                'category': SkillCategory.AUTOMATION,
                'level': 15,
                'experience_points': 150
            },
            {
                'skill_id': 'reasoning_basics',
                'name': 'Reasoning Basics',
                'category': SkillCategory.REASONING,
                'level': 25,
                'experience_points': 250
            },
            {
                'skill_id': 'communication_basics',
                'name': 'Communication Basics',
                'category': SkillCategory.COMMUNICATION,
                'level': 18,
                'experience_points': 180
            }
        ]
        
        for skill_data in base_skills:
            skill = Skill(**skill_data)
            self.skills[skill.skill_id] = skill
        
        self.logger.info(f"Initialized {len(base_skills)} base skills")
    
    def _build_skill_tree(self):
        """スキルツリー構築"""
        # 第1階層: 基本スキル
        self.skill_tree.add_node('basic_coding', [], {}, (0, 0))
        self.skill_tree.add_node('automation_basics', [], {}, (1, 0))
        self.skill_tree.add_node('reasoning_basics', [], {}, (2, 0))
        self.skill_tree.add_node('communication_basics', [], {}, (3, 0))
        
        # 第2階層: 応用スキル
        self.skill_tree.add_node('advanced_coding', ['basic_coding'], {'level': 30}, (0, 1))
        self.skill_tree.add_node('system_design', ['basic_coding', 'automation_basics'], 
                                {'level': 25}, (0.5, 1))
        self.skill_tree.add_node('complex_automation', ['automation_basics'], {'level': 30}, (1, 1))
        
        self.skill_tree.add_node('logical_reasoning', ['reasoning_basics'], {'level': 30}, (2, 1))
        self.skill_tree.add_node('creative_thinking', ['reasoning_basics', 'communication_basics'], 
                                {'level': 25}, (2.5, 1))
        
        self.skill_tree.add_node('natural_language', ['communication_basics'], {'level': 30}, (3, 1))
        
        # 第3階層: エキスパートスキル
        self.skill_tree.add_node('architectural_design', ['system_design', 'logical_reasoning'], 
                                {'level': 50}, (1, 2))
        self.skill_tree.add_node('ai_development', ['advanced_coding', 'logical_reasoning'], 
                                {'level': 50}, (0.5, 2))
        
        self.logger.info("Skill tree built")
    
    def use_skill(self, skill_id: str, success: bool):
        """スキル使用"""
        if skill_id not in self.skills:
            self.logger.error(f"Unknown skill: {skill_id}")
            return
        
        skill = self.skills[skill_id]
        leveled_up = skill.record_use(success)
        
        if leveled_up:
            self.logger.info(f"Skill {skill.name} leveled up to {skill.level}!")
        
        # 統計更新
        self._update_stats()
    
    def unlock_skill(self, skill_id: str) -> bool:
        """スキルアンロック"""
        # 既にアンロック済みかチェック
        if skill_id in self.skills:
            return False
        
        # アンロック可能かチェック
        unlockable = self.skill_tree.get_unlockable_skills(self.skills)
        if skill_id not in unlockable:
            self.logger.warning(f"Cannot unlock skill {skill_id}")
            return False
        
        # ノード情報取得
        node = self.skill_tree.nodes.get(skill_id)
        if not node:
            return False
        
        # 前提条件チェック
        for parent_id in node.parent_ids:
            if parent_id not in self.skills:
                return False
        
        # スキルアンロック
        category = self._get_category_from_name(skill_id)
        skill = Skill(
            skill_id=skill_id,
            name=self._get_display_name(skill_id),
            category=category
        )
        self.skills[skill_id] = skill
        
        self.logger.info(f"Unlocked skill: {skill.name}")
        self._update_stats()
        
        return True
    
    def _get_category_from_name(self, skill_id: str) -> SkillCategory:
        """スキル名からカテゴリー取得"""
        if 'coding' in skill_id or 'code' in skill_id:
            return SkillCategory.CODE
        elif 'automation' in skill_id:
            return SkillCategory.AUTOMATION
        elif 'reasoning' in skill_id:
            return SkillCategory.REASONING
        elif 'communication' in skill_id or 'language' in skill_id:
            return SkillCategory.COMMUNICATION
        elif 'analysis' in skill_id or 'design' in skill_id:
            return SkillCategory.ANALYSIS
        else:
            return SkillCategory.CODE
    
    def _get_display_name(self, skill_id: str) -> str:
        """表示名取得"""
        return skill_id.replace('_', ' ').title()
    
    def _update_stats(self):
        """統計更新"""
        if not self.skills:
            return
        
        # 合計レベル計算
        total_level = sum(skill.level for skill in self.skills.values())
        self.stats.total_level = total_level // len(self.skills)
        
        # 合計経験値
        self.stats.total_experience = sum(skill.experience_points for skill in self.skills.values())
        
        # アンロック済みスキル数
        self.stats.unlocked_skill_count = len(self.skills)
        
        # 合計試行回数
        self.stats.total_task_attempts = sum(skill.total_uses for skill in self.skills.values())
        
        # 合計成功数
        self.stats.total_task_successes = sum(skill.success_count for skill in self.skills.values())
        
        # 平均成功率
        if self.stats.total_task_attempts > 0:
            self.stats.average_success_rate = self.stats.total_task_successes / self.stats.total_task_attempts
        
        # 最高レベルスキル
        if self.skills:
            highest_skill = max(self.skills.values(), key=lambda s: s.level)
            self.stats.highest_level_skill = highest_skill.name
        
        # 最も使用されたスキル
        if self.skills:
            most_used = max(self.skills.values(), key=lambda s: s.total_uses)
            self.stats.most_used_skill = most_used.name
        
        # 専門性
        category_counts = {}
        for skill in self.skills.values():
            category = skill.category.value
            category_counts[category] = category_counts.get(category, 0) + skill.level
        
        if category_counts:
            self.stats.specialization = max(category_counts.items(), key=lambda x: x[1])[0]
    
    def get_skill_summary(self) -> Dict[str, Any]:
        """スキルサマリー取得"""
        return {
            'skills': {
                skill_id: {
                    'name': skill.name,
                    'category': skill.category.value,
                    'level': skill.level,
                    'level_name': skill.get_level_name(),
                    'experience': skill.experience_points,
                    'total_uses': skill.total_uses,
                    'success_rate': skill.get_success_rate()
                }
                for skill_id, skill in self.skills.items()
            },
            'unlockable': self.skill_tree.get_unlockable_skills(self.skills),
            'stats': asdict(self.stats)
        }
    
    def get_skill_tree_data(self) -> Dict[str, Any]:
        """スキルツリーデータ取得"""
        return {
            'nodes': {
                skill_id: {
                    'position': node.position,
                    'parents': node.parent_ids,
                    'unlocked': skill_id in self.skills
                }
                for skill_id, node in self.skill_tree.nodes.items()
            },
            'root_skills': self.skill_tree.root_skill_ids
        }
    
    def export_state(self) -> Dict[str, Any]:
        """状態エクスポート"""
        return {
            'skills': {
                skill_id: {
                    'name': skill.name,
                    'category': skill.category.value,
                    'level': skill.level,
                    'experience_points': skill.experience_points,
                    'total_uses': skill.total_uses,
                    'success_count': skill.success_count,
                    'failure_count': skill.failure_count
                }
                for skill_id, skill in self.skills.items()
            },
            'stats': asdict(self.stats),
            'timestamp': time.time()
        }
    
    def import_state(self, data: Dict[str, Any]):
        """状態インポート"""
        for skill_id, skill_data in data.get('skills', {}).items():
            category = SkillCategory(skill_data['category'])
            skill = Skill(
                skill_id=skill_id,
                name=skill_data['name'],
                category=category,
                level=skill_data['level'],
                experience_points=skill_data['experience_points'],
                total_uses=skill_data['total_uses'],
                success_count=skill_data['success_count'],
                failure_count=skill_data['failure_count']
            )
            self.skills[skill_id] = skill
        
        self._update_stats()
        self.logger.info("State imported successfully")

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # RPGシステム作成・テスト
    rpg = RPGSystem()
    
    print("RPG System Test")
    print("=" * 50)
    
    # スキルサマリー表示
    summary = rpg.get_skill_summary()
    print(f"Unlocked skills: {summary['stats']['unlocked_skill_count']}")
    print(f"Total level: {summary['stats']['total_level']}")
    print(f"Specialization: {summary['stats'].get('specialization', 'None')}")
    
    # スキル使用シミュレーション
    print("\n" + "=" * 50)
    print("Skill Usage Simulation")
    
    test_skills = [
        ('basic_coding', True),
        ('basic_coding', True),
        ('basic_coding', False),
        ('automation_basics', True),
        ('reasoning_basics', True)
    ]
    
    for skill_id, success in test_skills:
        rpg.use_skill(skill_id, success)
    
    # アンロック可能スキル表示
    unlockable = summary['unlockable']
    print(f"\nUnlockable skills: {len(unlockable)}")
    for skill_id in unlockable:
        print(f"  - {skill_id}")
    
    # 最終サマリー
    final_summary = rpg.get_skill_summary()
    print("\n" + "=" * 50)
    print("Final Summary:")
    print(json.dumps(final_summary['stats'], indent=2))
    
    print("\nRPG system test completed")