"""
OpenAPI/Swagger ドキュメント自動生成
Flask/FastAPI アプリケーションから OpenAPI 仕様を自動生成
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import re


class OpenAPISpecBuilder:
    """OpenAPI 3.0 仕様を生成"""
    
    def __init__(
        self,
        title: str = "ManaOS Unified API",
        description: str = "ManaOS統合API",
        version: str = "1.0.0",
        base_url: str = "http://localhost:9502"
    ):
        self.title = title
        self.description = description
        self.version = version
        self.base_url = base_url
        self.endpoints: List[Dict[str, Any]] = []
    
    def add_endpoint(
        self,
        path: str,
        method: str,
        summary: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        responses: Optional[Dict[str, Any]] = None,
        requires_auth: bool = False
    ):
        """エンドポイントを追加"""
        endpoint = {
            "path": path,
            "method": method.lower(),
            "summary": summary or f"{method} {path}",
            "description": description,
            "tags": tags or [],
            "parameters": parameters or [],
            "requestBody": request_body,
            "responses": responses or {
                "200": {"description": "Success"},
                "401": {"description": "Unauthorized"}
            },
            "security": [{"ApiKeyAuth": []}] if requires_auth else []
        }
        self.endpoints.append(endpoint)
    
    def build(self) -> Dict[str, Any]:
        """OpenAPI 仕様を構築"""
        # パスをグループ化
        paths: Dict[str, Dict[str, Any]] = {}
        for endpoint in self.endpoints:
            path = endpoint["path"]
            method = endpoint["method"]
            
            if path not in paths:
                paths[path] = {}
            
            paths[path][method] = {
                "summary": endpoint["summary"],
                "description": endpoint["description"],
                "tags": endpoint["tags"],
                "parameters": endpoint["parameters"],
                "responses": endpoint["responses"],
                "security": endpoint["security"]
            }
            
            if endpoint["requestBody"]:
                paths[path][method]["requestBody"] = endpoint["requestBody"]
        
        # OpenAPI 仕様
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "description": self.description,
                "version": self.version,
                "contact": {
                    "name": "MRL-mana",
                    "url": "https://github.com/MRL-mana/manaos-integrations"
                },
                "license": {
                    "name": "MIT"
                }
            },
            "servers": [
                {
                    "url": self.base_url,
                    "description": "Default server"
                }
            ],
            "paths": paths,
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "API Key for authentication"
                    }
                },
                "schemas": {
                    "Error": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "message": {"type": "string"},
                            "timestamp": {"type": "string"}
                        }
                    },
                    "HealthCheck": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "timestamp": {"type": "string"},
                            "service": {"type": "string"}
                        }
                    }
                }
            },
            "tags": [
                {"name": "Health", "description": "ヘルスチェック"},
                {"name": "API", "description": "統合API"},
                {"name": "LLM", "description": "LLM統合"},
                {"name": "Memory", "description": "メモリシステム"}
            ]
        }
        
        return spec
    
    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.build(), indent=2, ensure_ascii=False)
    
    def save_to_file(self, filepath: str) -> str:
        """ファイルに保存"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return str(path)


class FlaskOpenAPIExtractor:
    """Flask アプリケーションから OpenAPI 仕様を抽出"""
    
    @staticmethod
    def extract_from_app(app) -> OpenAPISpecBuilder:
        """Flask アプリケーションから仕様を抽出"""
        builder = OpenAPISpecBuilder()
        
        # ルートを走査
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith('_'):  # 内部ルートをスキップ
                continue
            
            methods = rule.methods - {'OPTIONS', 'HEAD'}
            for method in methods:
                # ドキュメント文字列からサマリーを抽出
                view_func = app.view_functions.get(rule.endpoint)
                summary = ""
                description = ""
                
                if view_func and view_func.__doc__:
                    doc = view_func.__doc__.strip().split('\n')
                    summary = doc[0] if doc else ""
                    description = '\n'.join(doc[1:]).strip() if len(doc) > 1 else ""
                
                # タグを決定
                tags = []
                if 'health' in str(rule).lower():
                    tags = ["Health"]
                elif '/api/llm' in str(rule):
                    tags = ["LLM"]
                elif '/api/memory' in str(rule):
                    tags = ["Memory"]
                elif '/api' in str(rule):
                    tags = ["API"]
                
                # 認証が必要か判定
                requires_auth = '/health' not in str(rule)
                
                builder.add_endpoint(
                    path=str(rule),
                    method=method,
                    summary=summary or f"{method} {rule}",
                    description=description,
                    tags=tags,
                    requires_auth=requires_auth
                )
        
        return builder


# 使用例
if __name__ == "__main__":
    # OpenAPI 仕様を手動作成
    builder = OpenAPISpecBuilder(
        title="ManaOS Unified API",
        version="1.0.0"
    )
    
    # ヘルスチェック
    builder.add_endpoint(
        "/health",
        "GET",
        summary="ヘルスチェック",
        tags=["Health"],
        responses={
            "200": {
                "description": "Service is healthy",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/HealthCheck"}
                    }
                }
            }
        },
        requires_auth=False
    )
    
    # 統合ステータス
    builder.add_endpoint(
        "/api/integrations/status",
        "GET",
        summary="統合モジュールの状態を取得",
        tags=["API"],
        responses={
            "200": {"description": "Integration status"},
            "401": {"description": "Unauthorized"}
        },
        requires_auth=True
    )
    
    # LLM 分析
    builder.add_endpoint(
        "/api/llm/analyze",
        "POST",
        summary="LLM分析を実行",
        tags=["LLM"],
        request_body={
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "model": {"type": "string"}
                        }
                    }
                }
            }
        },
        requires_auth=True
    )
    
    # メモリ保存
    builder.add_endpoint(
        "/api/memory/store",
        "POST",
        summary="メモリに情報を保存",
        tags=["Memory"],
        requires_auth=True
    )
    
    # 仕様を出力
    spec = builder.build()
    print("=" * 70)
    print("📋 OpenAPI 仕様サンプル")
    print("=" * 70)
    print(f"Title: {spec['info']['title']}")
    print(f"Version: {spec['info']['version']}")
    print(f"Endpoints: {len(spec['paths'])}")
    print("\n" + json.dumps(spec, indent=2, ensure_ascii=False)[:500] + "...\n")
    
    # ファイルに保存
    filepath = builder.save_to_file("monitoring/openapi/manaos-api-spec.json")
    print(f"✅ OpenAPI 仕様を保存しました: {filepath}")
