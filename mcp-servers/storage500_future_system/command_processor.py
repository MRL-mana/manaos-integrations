# MCP定型指令処理エンジン
import json
import re
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class CommandMatch:
    """指令マッチング結果"""
    pattern: str
    target: str
    action: str
    description: str
    category: str
    priority: str
    confidence: float
    context: str

class CommandProcessor:
    """定型指令処理エンジン"""
    
    def __init__(self, patterns_file: str = None):
        self.patterns_file = patterns_file or os.path.expanduser("~/mrl-mcp/commands/patterns.json")
        self.patterns = self._load_patterns()
        self.log_dir = os.path.expanduser("~/mrl-mcp/logs/commands")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.log_dir, 'command_processor.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_patterns(self) -> Dict:
        """パターンファイルを読み込み"""
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Patterns file not found: {self.patterns_file}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in patterns file: {e}")
            return {}
    
    def detect_commands(self, text: str) -> List[CommandMatch]:
        """テキストから定型指令を検出"""
        matches = []
        
        for pattern, config in self.patterns.items():
            # 完全一致
            if pattern in text:
                confidence = 1.0
                matches.append(CommandMatch(
                    pattern=pattern,
                    target=config.get('target', 'unknown'),
                    action=config.get('action', 'unknown'),
                    description=config.get('description', ''),
                    category=config.get('category', 'general'),
                    priority=config.get('priority', 'medium'),
                    confidence=confidence,
                    context=text
                ))
            # 部分一致（より柔軟な検出）
            elif self._fuzzy_match(pattern, text):
                confidence = 0.8
                matches.append(CommandMatch(
                    pattern=pattern,
                    target=config.get('target', 'unknown'),
                    action=config.get('action', 'unknown'),
                    description=config.get('description', ''),
                    category=config.get('category', 'general'),
                    priority=config.get('priority', 'medium'),
                    confidence=confidence,
                    context=text
                ))
        
        # 信頼度でソート
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
    
    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """曖昧マッチング"""
        # パターンのキーワードを分割
        keywords = pattern.split()
        
        # テキストにキーワードが含まれているかチェック
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def execute_command(self, match: CommandMatch, content: str = "") -> Dict:
        """指令を実行"""
        try:
            self.logger.info(f"Executing command: {match.pattern} -> {match.target}.{match.action}")
            
            # 指令ログを保存
            self._log_command(match, content)
            
            # ターゲット別の処理
            if match.target == "claude":
                return self._execute_claude_command(match, content)
            elif match.target == "n8n":
                return self._execute_n8n_command(match, content)
            elif match.target == "slack":
                return self._execute_slack_command(match, content)
            elif match.target == "obsidian":
                return self._execute_obsidian_command(match, content)
            elif match.target == "system":
                return self._execute_system_command(match, content)
            else:
                return {"status": "error", "message": f"Unknown target: {match.target}"}
                
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return {"status": "error", "message": str(e)}
    
    def _execute_claude_command(self, match: CommandMatch, content: str) -> Dict:
        """Claude指令の実行"""
        # Claude APIに送信する処理
        prompt = f"指令: {match.pattern}\n内容: {content}\n\n{match.description}"
        
        # ここでClaude APIを呼び出す
        # 実際の実装ではClaude APIクライアントを使用
        
        return {
            "status": "success",
            "target": "claude",
            "action": match.action,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_n8n_command(self, match: CommandMatch, content: str) -> Dict:
        """n8n指令の実行"""
        try:
            from mcp_trigger_n8n_improved import trigger_n8n
            
            data = {
                "type": "command_execution",
                "command": match.pattern,
                "action": match.action,
                "content": content,
                "target": match.target
            }
            
            result = trigger_n8n(data)
            
            return {
                "status": "success" if result else "error",
                "target": "n8n",
                "action": match.action,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {"status": "error", "message": "n8n module not available"}
    
    def _execute_slack_command(self, match: CommandMatch, content: str) -> Dict:
        """Slack指令の実行"""
        try:
            from mcp_notify_slack_improved import notify_slack
            
            message = f"📝 指令実行: {match.pattern}\n\n{content}"
            result = notify_slack(message)
            
            return {
                "status": "success" if result else "error",
                "target": "slack",
                "action": match.action,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {"status": "error", "message": "Slack module not available"}
    
    def _execute_obsidian_command(self, match: CommandMatch, content: str) -> Dict:
        """Obsidian指令の実行"""
        # Obsidian連携の実装
        # 実際の実装ではObsidian APIを使用
        
        return {
            "status": "success",
            "target": "obsidian",
            "action": match.action,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_system_command(self, match: CommandMatch, content: str) -> Dict:
        """システム指令の実行"""
        if match.action == "backup":
            # バックアップ処理
            return self._execute_backup()
        elif match.action == "monitor":
            # 監視処理
            return self._execute_monitor()
        elif match.action == "optimize":
            # 最適化処理
            return self._execute_optimize()
        else:
            return {"status": "error", "message": f"Unknown system action: {match.action}"}
    
    def _execute_backup(self) -> Dict:
        """バックアップ実行"""
        try:
            # バックアップ処理の実装
            backup_dir 