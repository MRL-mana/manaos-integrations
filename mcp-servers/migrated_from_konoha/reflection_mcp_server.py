#!/usr/bin/env python3
"""
Reflection MCP Server - ManaOS統合用

ManaOSの各サービスからReflection Engineに行動/結果を記録するためのMCPサーバー
"""

import sys
import json
from pathlib import Path

# Reflection Engineをインポート
workspace = Path("/root/trinity_workspace")
sys.path.insert(0, str(workspace / "bridge"))
from reflection_engine import ReflectionEngine


class ReflectionMCPServer:
    """Reflection MCP Server"""
    
    def __init__(self):
        self.engine = ReflectionEngine()
        self.capabilities = {
            "tools": [
                {
                    "name": "record_action",
                    "description": "AIエージェントの行動を記録",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "description": "エージェント名（remi/luna/mina/aria/manaos）"
                            },
                            "action_type": {
                                "type": "string",
                                "description": "行動タイプ（例: image_generation, weather_check, email_send）"
                            },
                            "context": {
                                "type": "string",
                                "description": "行動のコンテキスト"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "判断理由",
                                "default": ""
                            },
                            "confidence": {
                                "type": "number",
                                "description": "信頼度（0.0-1.0）",
                                "default": 0.5
                            }
                        },
                        "required": ["agent", "action_type", "context"]
                    }
                },
                {
                    "name": "record_outcome",
                    "description": "行動の結果を記録",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action_id": {
                                "type": "integer",
                                "description": "行動ID（record_actionの戻り値）"
                            },
                            "success": {
                                "type": "boolean",
                                "description": "成功/失敗"
                            },
                            "actual_result": {
                                "type": "string",
                                "description": "実際の結果"
                            },
                            "expected_result": {
                                "type": "string",
                                "description": "期待していた結果"
                            }
                        },
                        "required": ["action_id", "success", "actual_result", "expected_result"]
                    }
                },
                {
                    "name": "get_learned_patterns",
                    "description": "学習済みパターンを取得",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "description": "エージェント名（省略時は全エージェント）"
                            },
                            "pattern_type": {
                                "type": "string",
                                "description": "パターンタイプ（省略時は全タイプ）"
                            }
                        }
                    }
                },
                {
                    "name": "get_qsr_score",
                    "description": "QSR（品質自己反省）スコアを取得",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "description": "エージェント名（省略時は全エージェント）"
                            },
                            "days": {
                                "type": "integer",
                                "description": "過去N日間（デフォルト: 7）",
                                "default": 7
                            }
                        }
                    }
                },
                {
                    "name": "get_improvements",
                    "description": "改善提案を取得",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "description": "エージェント名（省略時は全エージェント）"
                            },
                            "days": {
                                "type": "integer",
                                "description": "過去N日間（デフォルト: 7）",
                                "default": 7
                            }
                        }
                    }
                }
            ]
        }
    
    def handle_call_tool(self, tool_name: str, arguments: dict) -> dict:
        """ツール呼び出しを処理"""
        try:
            if tool_name == "record_action":
                action_id = self.engine.record_action(  # type: ignore[call-arg]
                    agent=arguments['agent'],
                    action_type=arguments['action_type'],
                    context=arguments['context'],
                    decision_reasoning=arguments.get('reasoning', ''),  # type: ignore[call-arg]
                    confidence=arguments.get('confidence', 0.5)
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "action_id": action_id,
                                "message": f"行動を記録しました（ID: {action_id}）"
                            }, ensure_ascii=False)
                        }
                    ]
                }
            
            elif tool_name == "record_outcome":
                deviation = self.engine.record_outcome(
                    action_id=arguments['action_id'],
                    success=arguments['success'],
                    actual_result=arguments['actual_result'],
                    expected_result=arguments['expected_result']
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "deviation_score": deviation,
                                "message": f"結果を記録しました（偏差: {deviation:.3f}）"
                            }, ensure_ascii=False)
                        }
                    ]
                }
            
            elif tool_name == "get_learned_patterns":
                patterns = self.engine.get_learned_patterns(  # type: ignore
                    agent=arguments.get('agent'),
                    pattern_type=arguments.get('pattern_type')
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "patterns": patterns,
                                "count": len(patterns)
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            elif tool_name == "get_qsr_score":
                qsr = self.engine.calculate_qsr(
                    agent=arguments.get('agent'),
                    days=arguments.get('days', 7)
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "qsr": qsr
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            elif tool_name == "get_improvements":
                improvements = self.engine.generate_improvements(
                    agent=arguments.get('agent'),
                    days=arguments.get('days', 7)
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "improvements": improvements,
                                "count": len(improvements)
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"Unknown tool: {tool_name}"
                            })
                        }
                    ],
                    "isError": True
                }
        
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": str(e)
                        })
                    }
                ],
                "isError": True
            }
    
    def run(self):
        """MCPサーバーとして実行"""
        # 標準入出力でJSON-RPCメッセージを処理
        for line in sys.stdin:
            try:
                request = json.loads(line)
                
                if request.get('method') == 'initialize':
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get('id'),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": self.capabilities,
                            "serverInfo": {
                                "name": "reflection-mcp-server",
                                "version": "1.0.0"
                            }
                        }
                    }
                    print(json.dumps(response), flush=True)
                
                elif request.get('method') == 'tools/call':
                    params = request.get('params', {})
                    tool_name = params.get('name')
                    arguments = params.get('arguments', {})
                    
                    result = self.handle_call_tool(tool_name, arguments)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get('id'),
                        "result": result
                    }
                    print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get('id') if 'request' in locals() else None,  # type: ignore[possibly-unbound]
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                print(json.dumps(error_response), flush=True)


def main():
    server = ReflectionMCPServer()
    server.run()


if __name__ == "__main__":
    main()

