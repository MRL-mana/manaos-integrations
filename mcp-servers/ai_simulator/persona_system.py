"""
AI Simulator Virtual Persona System
仮想人間生成システム（安全な並行人格）

注：リアル人格化ではなく、役割AIとして実装
「人格的」ではなく、目的関数が違う「議会モデル」
"""

import numpy as np
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class PersonaRole(Enum):
    """人格役割"""
    ANALYST = "analyst"      # 分析者
    CREATOR = "creator"      # 創造者
    OPTIMIZER = "optimizer"  # 最適化者
    GUARDIAN = "guardian"    # 保護者
    EXPLORER = "explorer"    # 探検者
    CONNECTOR = "connector"  # 結合者

class PersonalityTrait(Enum):
    """性格特性"""
    RISK_TAKING = "risk_taking"
    CREATIVITY = "creativity"
    CONSERVATIVENESS = "conservativeness"
    OPTIMISM = "optimism"
    PRAGMATISM = "pragmatism"
    CURIOUSNESS = "curiousness"

@dataclass
class PersonaProfile:
    """人格プロファイル"""
    persona_id: str
    name: str
    role: PersonaRole
    traits: Dict[PersonalityTrait, float] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    expertise_areas: List[str] = field(default_factory=list)
    opinion_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_opinion_weight(self, context: str) -> float:
        """コンテキストに基づく意見重み付け"""
        # 役割と専門性に基づく重み付け
        weight = 1.0
        
        # 専門分野なら高重み
        if any(area in context.lower() for area in self.expertise_areas):
            weight += 0.5
        
        # 性格特性による調整
        if PersonalityTrait.CURIOUSNESS in self.traits:
            if "exploration" in context.lower():
                weight += self.traits[PersonalityTrait.CURIOUSNESS] * 0.3
        
        if PersonalityTrait.CREATIVITY in self.traits:
            if "creative" in context.lower() or "innovation" in context.lower():
                weight += self.traits[PersonalityTrait.CREATIVITY] * 0.3
        
        return weight

@dataclass
class DecisionProposal:
    """決定提案"""
    persona_id: str
    proposal: Dict[str, Any]
    rationale: str
    confidence: float
    timestamp: float
    
@dataclass
class ConsensusDecision:
    """合意形成決定"""
    decision: Dict[str, Any]
    consensus_score: float
    participant_count: int
    dissenting_views: List[str]
    consensus_method: str

class VirtualPersona:
    """仮想人格"""
    
    def __init__(self, profile: PersonaProfile):
        self.profile = profile
        self.logger = self._setup_logger()
        
        # 内部状態
        self.active_context = None
        self.recent_decisions = []
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger(f'persona_{self.profile.persona_id}')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(f'/app/logs/persona_{self.profile.persona_id}.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def propose(self, context: Dict[str, Any]) -> DecisionProposal:
        """提案生成"""
        self.active_context = context
        
        # 役割に基づく提案生成
        proposal = self._generate_proposal(context)
        rationale = self._generate_rationale(context, proposal)
        confidence = self._calculate_confidence(context, proposal)
        
        decision_proposal = DecisionProposal(
            persona_id=self.profile.persona_id,
            proposal=proposal,
            rationale=rationale,
            confidence=confidence,
            timestamp=time.time()
        )
        
        # 履歴記録
        self.profile.opinion_history.append({
            'timestamp': time.time(),
            'proposal': proposal,
            'rationale': rationale,
            'confidence': confidence
        })
        
        self.logger.info(f"Proposal generated: {rationale}")
        
        return decision_proposal
    
    def _generate_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """提案生成（役割ごとのロジック）"""
        if self.profile.role == PersonaRole.ANALYST:
            return self._analyst_proposal(context)
        elif self.profile.role == PersonaRole.CREATOR:
            return self._creator_proposal(context)
        elif self.profile.role == PersonaRole.OPTIMIZER:
            return self._optimizer_proposal(context)
        elif self.profile.role == PersonaRole.GUARDIAN:
            return self._guardian_proposal(context)
        elif self.profile.role == PersonaRole.EXPLORER:
            return self._explorer_proposal(context)
        elif self.profile.role == PersonaRole.CONNECTOR:
            return self._connector_proposal(context)
        else:
            return {}
    
    def _analyst_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析者提案"""
        return {
            'action': 'analyze',
            'focus_areas': context.get('data_fields', []),
            'depth': 'deep',
            'output_format': 'structured'
        }
    
    def _creator_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """創造者提案"""
        return {
            'action': 'create',
            'approach': 'innovative',
            'constraints': 'minimal',
            'exploration': 'high'
        }
    
    def _optimizer_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """最適化者提案"""
        return {
            'action': 'optimize',
            'metrics': ['efficiency', 'resource_usage'],
            'method': 'iterative_refinement'
        }
    
    def _guardian_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """保護者提案"""
        return {
            'action': 'protect',
            'security_checks': ['all'],
            'risk_assessment': 'thorough',
            'safety_first': True
        }
    
    def _explorer_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """探検者提案"""
        return {
            'action': 'explore',
            'breadth': 'wide',
            'depth': 'shallow',
            'novelty_priority': True
        }
    
    def _connector_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """結合者提案"""
        return {
            'action': 'connect',
            'integration_points': context.get('related_systems', []),
            'coordination': 'high',
            'synergy_focus': True
        }
    
    def _generate_rationale(self, context: Dict[str, Any], proposal: Dict[str, Any]) -> str:
        """根拠生成"""
        role_name = self.profile.role.value
        rationale = f"As {self.profile.name} ({role_name}), I propose: {proposal.get('action', 'N/A')}"
        
        # 性格特性による補足
        if PersonalityTrait.CREATIVITY in self.profile.traits:
            if self.profile.traits[PersonalityTrait.CREATIVITY] > 0.7:
                rationale += " Emphasizing creative approaches."
        
        if PersonalityTrait.CONSERVATIVENESS in self.profile.traits:
            if self.profile.traits[PersonalityTrait.CONSERVATIVENESS] > 0.7:
                rationale += " Prioritizing stability and proven methods."
        
        return rationale
    
    def _calculate_confidence(self, context: Dict[str, Any], proposal: Dict[str, Any]) -> float:
        """信頼度計算"""
        base_confidence = 0.5
        
        # 専門分野なら高信頼度
        if any(area in str(context).lower() for area in self.profile.expertise_areas):
            base_confidence += 0.3
        
        # 性格特性による調整
        if PersonalityTrait.CREATIVITY in self.profile.traits:
            base_confidence += self.profile.traits[PersonalityTrait.CREATIVITY] * 0.1
        
        # 過去の成功実績
        if self.recent_decisions:
            success_count = sum(1 for d in self.recent_decisions[-10:] if d.get('success', False))
            base_confidence += (success_count / len(self.recent_decisions[-10:])) * 0.2
        
        return min(1.0, max(0.0, base_confidence))
    
    def evaluate(self, proposal: DecisionProposal, context: Dict[str, Any]) -> float:
        """提案評価"""
        score = 0.5
        
        # 役割との適合性
        if self.profile.role == PersonaRole.ANALYST:
            if proposal.proposal.get('action') == 'analyze':
                score += 0.2
        
        # 性格特性との適合性
        if PersonalityTrait.RISK_TAKING in self.profile.traits:
            if self.profile.traits[PersonalityTrait.RISK_TAKING] > 0.7:
                score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def get_persona_state(self) -> Dict[str, Any]:
        """人格状態取得"""
        return {
            'persona_id': self.profile.persona_id,
            'name': self.profile.name,
            'role': self.profile.role.value,
            'traits': {k.value: v for k, v in self.profile.traits.items()},
            'expertise_areas': self.profile.expertise_areas,
            'recent_opinions': len(self.profile.opinion_history),
            'active_context': self.active_context
        }

class PersonaManager:
    """人格マネージャー"""
    
    def __init__(self):
        self.personas: Dict[str, VirtualPersona] = {}
        self.logger = self._setup_logger()
        self._initialize_default_personas()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('persona_manager')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/persona_manager.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_default_personas(self):
        """デフォルト人格初期化"""
        # Remi - 戦略指令AI（設計者）
        remi = self._create_persona(
            persona_id="remi",
            name="Remi",
            role=PersonaRole.ANALYST,
            traits={
                PersonalityTrait.PRAGMATISM: 0.9,
                PersonalityTrait.CURIOUSNESS: 0.7,
                PersonalityTrait.CREATIVITY: 0.5
            },
            expertise_areas=["strategy", "architecture", "task_decomposition", "system_design"],
            preferences={"focus": "planning", "approach": "strategic"}
        )
        
        # Luna - 実務遂行AI（実装者）
        luna = self._create_persona(
            persona_id="luna",
            name="Luna",
            role=PersonaRole.CREATOR,
            traits={
                PersonalityTrait.CREATIVITY: 0.9,
                PersonalityTrait.OPTIMISM: 0.8,
                PersonalityTrait.RISK_TAKING: 0.6,
                PersonalityTrait.PRAGMATISM: 0.7
            },
            expertise_areas=["implementation", "coding", "problem_solving", "optimization"],
            preferences={"focus": "execution", "approach": "efficient"}
        )
        
        # Mina - 洞察記録AI（レビュー・QA）
        mina = self._create_persona(
            persona_id="mina",
            name="Mina",
            role=PersonaRole.GUARDIAN,
            traits={
                PersonalityTrait.CONSERVATIVENESS: 0.9,
                PersonalityTrait.PRAGMATISM: 0.8,
                PersonalityTrait.CREATIVITY: 0.4,
                PersonalityTrait.CURIOUSNESS: 0.6
            },
            expertise_areas=["quality_assurance", "testing", "review", "analysis"],
            preferences={"focus": "quality", "approach": "thorough"}
        )
        
        self.personas["remi"] = remi
        self.personas["luna"] = luna
        self.personas["mina"] = mina
        
        self.logger.info(f"Initialized {len(self.personas)} default personas")
    
    def _create_persona(self, persona_id: str, name: str, role: PersonaRole, 
                        traits: Dict[PersonalityTrait, float],
                        expertise_areas: List[str],
                        preferences: Dict[str, Any]) -> VirtualPersona:
        """人格作成"""
        profile = PersonaProfile(
            persona_id=persona_id,
            name=name,
            role=role,
            traits=traits,
            preferences=preferences,
            expertise_areas=expertise_areas
        )
        
        return VirtualPersona(profile)
    
    def get_persona(self, persona_id: str) -> Optional[VirtualPersona]:
        """人格取得"""
        return self.personas.get(persona_id)
    
    def get_all_personas(self) -> List[VirtualPersona]:
        """全人格取得"""
        return list(self.personas.values())
    
    def create_consensus(self, context: Dict[str, Any]) -> ConsensusDecision:
        """合意形成"""
        self.logger.info(f"Creating consensus for context: {context}")
        
        # 各人格から提案取得
        proposals = []
        for persona in self.personas.values():
            proposal = persona.propose(context)
            proposals.append(proposal)
        
        # 提案評価
        evaluations = {}
        for proposal in proposals:
            for persona in self.personas.values():
                score = persona.evaluate(proposal, context)
                if proposal.persona_id not in evaluations:
                    evaluations[proposal.persona_id] = []
                evaluations[proposal.persona_id].append(score)
        
        # 平均評価計算
        avg_scores = {
            pid: np.mean(scores) for pid, scores in evaluations.items()
        }
        
        # 重み付き合意
        consensus_proposal = self._weighted_consensus(proposals, avg_scores)
        
        # 反対意見
        dissenting_views = [
            f"{p.rationale} (confidence: {p.confidence:.2f})" 
            for p in proposals 
            if p.confidence < 0.5
        ]
        
        decision = ConsensusDecision(
            decision=consensus_proposal,
            consensus_score=np.mean(list(avg_scores.values())),
            participant_count=len(self.personas),
            dissenting_views=dissenting_views,
            consensus_method="weighted_average"
        )
        
        self.logger.info(f"Consensus reached: {decision.consensus_score:.2f}")
        
        return decision
    
    def _weighted_consensus(self, proposals: List[DecisionProposal], 
                           scores: Dict[str, float]) -> Dict[str, Any]:
        """重み付き合意"""
        # 最も高評価された提案を選択
        best_proposal = max(proposals, key=lambda p: scores.get(p.persona_id, 0.0))
        return best_proposal.proposal
    
    def get_council_state(self) -> Dict[str, Any]:
        """評議会状態取得"""
        return {
            'personas': [persona.get_persona_state() for persona in self.personas.values()],
            'total_personas': len(self.personas),
            'roles': [p.profile.role.value for p in self.personas.values()]
        }

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # 人格マネージャー作成・テスト
    manager = PersonaManager()
    
    print("Virtual Persona System Test")
    print("=" * 50)
    
    # 評議会状態表示
    council_state = manager.get_council_state()
    print(f"\nCouncil State: {council_state['total_personas']} personas")
    for persona_state in council_state['personas']:
        print(f"  - {persona_state['name']} ({persona_state['role']})")
    
    # 合意形成テスト
    test_context = {
        'task': 'optimize_system',
        'data_fields': ['performance', 'efficiency', 'cost'],
        'constraints': ['security', 'stability']
    }
    
    print("\n" + "=" * 50)
    print(f"Consensus Test: {test_context['task']}")
    
    consensus = manager.create_consensus(test_context)
    
    print(f"\nConsensus Score: {consensus.consensus_score:.2f}")
    print(f"Decision: {consensus.decision}")
    print(f"Participants: {consensus.participant_count}")
    
    if consensus.dissenting_views:
        print(f"\nDissenting Views: {len(consensus.dissenting_views)}")
        for view in consensus.dissenting_views[:2]:
            print(f"  - {view}")
    
    print("\nVirtual persona system test completed")