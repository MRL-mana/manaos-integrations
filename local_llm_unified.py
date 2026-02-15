"""
ローカルLLM統合モジュール
複数のローカルLLMリポジトリを統合
"""

import os
from manaos_logger import get_logger
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = get_logger(__name__)


class LocalLLMUnified:
    """複数のローカルLLMシステムを統合"""
    
    def __init__(self):
        """初期化"""
        self.repos_path = Path("repos")
        self.available_systems = {}
        self._check_available_systems()
    
    def _check_available_systems(self):
        """利用可能なシステムを確認"""
        # Sara-AI-Platform
        sara_path = self.repos_path / "Sara-AI-Platform" / "backend"
        if sara_path.exists():
            self.available_systems["sara"] = {
                "path": str(sara_path),
                "type": "full_stack",
                "features": ["memory", "persona", "tts", "multi_model_routing"]
            }
        
        # Auto-Deep-Research
        auto_research_path = self.repos_path / "Auto-Deep-Research"
        if auto_research_path.exists():
            self.available_systems["auto_research"] = {
                "path": str(auto_research_path),
                "type": "research_agent",
                "features": ["deep_research", "file_processing", "web_surfing"]
            }
        
        # Free-personal-AI-Assistant
        free_assistant_path = self.repos_path / "Free-personal-AI-Assistant-with-plugin"
        if free_assistant_path.exists():
            self.available_systems["free_assistant"] = {
                "path": str(free_assistant_path),
                "type": "chatbot",
                "features": ["plugins", "web_search", "pdf", "youtube"]
            }
        
        # personal-ai-assistant
        personal_assistant_path = self.repos_path / "personal-ai-assistant"
        if personal_assistant_path.exists():
            self.available_systems["personal_assistant"] = {
                "path": str(personal_assistant_path),
                "type": "multi_agent",
                "features": ["messaging", "email", "schedule", "research"]
            }
        
        # personal-ai-starter-pack
        starter_pack_path = self.repos_path / "personal-ai-starter-pack"
        if starter_pack_path.exists():
            self.available_systems["starter_pack"] = {
                "path": str(starter_pack_path),
                "type": "voice_assistant",
                "features": ["stt", "tts", "fast_response"]
            }
        
        # Ollama-local-llm-python
        ollama_local_path = self.repos_path / "Ollama-local-llm-python"
        if ollama_local_path.exists():
            self.available_systems["ollama_local"] = {
                "path": str(ollama_local_path),
                "type": "llm_wrapper",
                "features": ["ollama", "privacy", "local"]
            }
    
    def get_available_systems(self) -> Dict[str, Dict]:
        """利用可能なシステム一覧を取得"""
        return self.available_systems
    
    def get_system_by_feature(self, feature: str) -> List[str]:
        """特定の機能を持つシステムを検索"""
        systems = []
        for name, info in self.available_systems.items():
            if feature in info.get("features", []):
                systems.append(name)
        return systems
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス情報を取得"""
        return {
            "available_systems": list(self.available_systems.keys()),
            "total_systems": len(self.available_systems),
            "systems": self.available_systems
        }


# 使用例
if __name__ == "__main__":
    unified = LocalLLMUnified()
    
    print("利用可能なシステム:")
    for name, info in unified.get_available_systems().items():
        print(f"  - {name}: {info['type']}")
        print(f"    機能: {', '.join(info['features'])}")
    
    print("\nステータス:")
    status = unified.get_status()
    print(f"  合計: {status['total_systems']} システム")
    
    # 機能で検索
    print("\nメモリ機能を持つシステム:")
    memory_systems = unified.get_system_by_feature("memory")
    for sys in memory_systems:
        print(f"  - {sys}")


















