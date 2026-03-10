#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📚 ManaOS API仕様書自動生成
OpenAPI/Swagger形式のAPI仕様書を生成
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


def generate_openapi_spec() -> Dict[str, Any]:
    """OpenAPI仕様を生成"""
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "ManaOS統合API",
            "description": "ManaOS統合システムのAPI仕様書",
            "version": "1.0.0",
            "contact": {
                "name": "ManaOS Support",
                "email": "support@manaos.local"
            }
        },
        "servers": [
            {
                "url": "http://127.0.0.1:5000",
                "description": "ローカル開発環境"
            },
            {
                "url": "https://api.manaos.local",
                "description": "本番環境"
            }
        ],
        "tags": [
            {"name": "Health", "description": "ヘルスチェック"},
            {"name": "Services", "description": "サービス管理"},
            {"name": "LLM", "description": "LLM関連API"},
            {"name": "Integration", "description": "統合システム"},
            {"name": "Security", "description": "セキュリティ"},
            {"name": "Metrics", "description": "メトリクス"},
            {"name": "Backup", "description": "バックアップ"}
        ],
        "paths": {
            "/health": {
                "get": {
                    "tags": ["Health"],
                    "summary": "ヘルスチェック",
                    "responses": {
                        "200": {
                            "description": "正常",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"},
                                            "timestamp": {"type": "string", "format": "date-time"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/services/status": {
                "get": {
                    "tags": ["Services"],
                    "summary": "サービス状態取得",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "services": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "object",
                                                    "properties": {
                                                        "available": {"type": "boolean"},
                                                        "status_code": {"type": "integer"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"description": "認証エラー"}
                    }
                }
            },
            "/api/llm/chat": {
                "post": {
                    "tags": ["LLM"],
                    "summary": "LLMチャット",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["input_text"],
                                    "properties": {
                                        "input_text": {
                                            "type": "string",
                                            "description": "入力テキスト",
                                            "maxLength": 10000
                                        },
                                        "mode": {
                                            "type": "string",
                                            "enum": ["auto", "manual", "interactive"],
                                            "default": "auto"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "response": {"type": "string"},
                                            "model": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {"description": "バリデーションエラー"},
                        "401": {"description": "認証エラー"},
                        "429": {"description": "レート制限エラー"}
                    }
                }
            },
            "/api/metrics": {
                "get": {
                    "tags": ["Metrics"],
                    "summary": "メトリクス取得",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "metrics": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "value": {"type": "number"},
                                                        "timestamp": {"type": "string", "format": "date-time"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/backup": {
                "post": {
                    "tags": ["Backup"],
                    "summary": "バックアップ作成",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "target_type": {
                                            "type": "string",
                                            "enum": ["all", "databases", "configs", "logs"],
                                            "default": "all"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "backup_path": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "code": {"type": "string"},
                        "message": {"type": "string"}
                    }
                }
            }
        }
    }
    
    return spec


def save_openapi_spec(output_path: Path = None):  # type: ignore
    """OpenAPI仕様を保存"""
    if output_path is None:
        output_path = Path(__file__).parent / "docs" / "openapi.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    spec = generate_openapi_spec()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    
    print(f"✅ OpenAPI仕様書を保存しました: {output_path}")
    return output_path


if __name__ == "__main__":
    save_openapi_spec()








