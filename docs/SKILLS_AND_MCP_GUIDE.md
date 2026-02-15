# ManaOS スキルとMCP統合ガイド

このガイドでは、VSCode/Cursorスキルとして利用できるMCPサーバーの統合方法を説明します。

## 目次
1. [スキルシステム概要](#スキルシステム概要)
2. [利用可能なスキル](#利用可能なスキル)
3. [カスタムスキルの作成](#カスタムスキルの作成)
4. [MCP統合パターン](#mcp統合パターン)
5. [実践例](#実践例)

---

## スキルシステム概要

ManaOSのスキルシステムは、AIアシスタントが特定のタスクを実行するための再利用可能な能力です。

### スキルの構成要素

```
skill/
├── skill.json          # スキル定義
├── main.py             # メインロジック
├── requirements.txt    # 依存関係
└── README.md           # ドキュメント
```

### skill.json の例

```json
{
  "name": "code_analyzer",
  "version": "1.0.0",
  "description": "コードを分析し改善提案を行う",
  "mcp_servers": ["unified_api", "mrl_memory"],
  "capabilities": [
    "analyze_code",
    "suggest_improvements",
    "detect_bugs"
  ],
  "triggers": [
    "コードを分析",
    "改善提案",
    "バグ検出"
  ]
}
```

---

## 利用可能なスキル

### 1. コード生成スキル

**トリガー:** "コードを生成"、"実装して"

**機能:**
- LLMルーティングで最適なモデル選択
- コード品質チェック
- 自動テスト生成

**使用例:**
```
User: "ファイルをS3にアップロードする関数を実装して"
Assistant: [LLM Routing → Code Generation → Quality Check]
```

### 2. メモリ統合スキル

**トリガー:** "覚えておいて"、"思い出して"

**機能:**
- 重要情報の自動保存
- コンテキスト検索
- 関連情報の提示

**使用例:**
```
User: "このプロジェクトではポート9502を使うことを覚えておいて"
Assistant: [MRL Memory Store → Confirmation]
```

### 3. 画像生成スキル

**トリガー:** "画像を生成"、"イラストを作って"

**機能:**
- ComfyUI/Stable Diffusion統合
- スタイル最適化
- ギャラリー保存

**使用例:**
```
User: "サンセットの風景画像を生成して"
Assistant: [ComfyUI → Generate → Gallery Save]
```

### 4. 動画処理スキル

**トリガー:** "動画を作成"、"動画編集"

**機能:**
- 動画生成パイプライン
- スタイル転送
- 自動編集

**使用例:**
```
User: "この画像からシネマティックな動画を作成"
Assistant: [Video Pipeline → Style Transfer → Export]
```

### 5. システム自動化スキル

**トリガー:** "自動化して"、"タスクを実行"

**機能:**
- Pico HIDでUI操作
- スクリプト実行
- スケジュール管理

**使用例:**
```
User: "毎日8時にレポートを生成して"
Assistant: [Task Scheduler → Script Generation → Automation Setup]
```

---

## カスタムスキルの作成

### ステップ1: テンプレート

```python
# skills/my_skill/main.py
from typing import Dict, Any
from config_loader import get_service_url
import requests

class MySkill:
    """カスタムスキルの実装"""
    
    def __init__(self):
        self.name = "my_skill"
        self.version = "1.0.0"
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        スキルのメイン実行ロジック
        
        Args:
            params: 実行パラメータ
            
        Returns:
            実行結果
        """
        try:
            # Unified API経由で処理
            url = f"{get_service_url('unified_api')}/process"
            response = requests.post(url, json=params)
            
            return {
                "success": True,
                "result": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """パラメータのバリデーション"""
        required_fields = ['input_data', 'options']
        return all(field in params for field in required_fields)

# スキルのエントリポイント
def create_skill():
    return MySkill()
```

### ステップ2: skill.json

```json
{
  "name": "my_skill",
  "version": "1.0.0",
  "description": "カスタムスキルの説明",
  "author": "Your Name",
  "mcp_servers": ["unified_api"],
  "capabilities": [
    "process_data",
    "analyze_results"
  ],
  "triggers": [
    "データを処理",
    "解析して"
  ],
  "parameters": {
    "input_data": {
      "type": "string",
      "required": true,
      "description": "入力データ"
    },
    "options": {
      "type": "object",
      "required": false,
      "description": "オプション設定"
    }
  }
}
```

### ステップ3: requirements.txt

```
requests>=2.28.0
python-dotenv>=0.19.0
```

### ステップ4: VSCode統合

`.vscode/skills.json`:

```json
{
  "skills": [
    {
      "name": "my_skill",
      "path": "./skills/my_skill",
      "enabled": true,
      "priority": 10
    }
  ]
}
```

---

## MCP統合パターン

### パターン1: 直接呼び出し

```python
import requests
from config_loader import get_service_url

def call_mcp_direct(service_name: str, endpoint: str, data: dict):
    """MCPサーバーを直接呼び出し"""
    url = f"{get_service_url(service_name)}{endpoint}"
    response = requests.post(url, json=data)
    return response.json()

# 使用例
result = call_mcp_direct('mrl_memory', '/search', {'query': 'Python'})
```

### パターン2: Unified API経由

```python
def call_mcp_via_unified(service_name: str, endpoint: str, data: dict):
    """Unified API経由でMCPサーバーを呼び出し"""
    url = f"{get_service_url('unified_api')}/mcp/{service_name}{endpoint}"
    response = requests.post(url, json=data)
    return response.json()

# 使用例
result = call_mcp_via_unified('llm_routing', '/route', {'prompt': 'Hello'})
```

### パターン3: チェーン呼び出し

```python
def chain_mcp_calls(operations: list):
    """複数のMCPサーバーをチェーン呼び出し"""
    result = {}
    
    for op in operations:
        service = op['service']
        endpoint = op['endpoint']
        data = op.get('data', {})
        
        # 前の結果を次の入力に
        if result:
            data['previous_result'] = result
        
        result = call_mcp_direct(service, endpoint, data)
    
    return result

# 使用例
operations = [
    {'service': 'llm_routing', 'endpoint': '/analyze', 'data': {'text': 'Hello'}},
    {'service': 'mrl_memory', 'endpoint': '/store', 'data': {}}
]
result = chain_mcp_calls(operations)
```

### パターン4: 並列実行

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_mcp_calls(calls: list):
    """複数のMCPサーバーを並列呼び出し"""
    results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                call_mcp_direct,
                call['service'],
                call['endpoint'],
                call.get('data', {})
            ): call['name']
            for call in calls
        }
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {'error': str(e)}
    
    return results

# 使用例
calls = [
    {'name': 'memory', 'service': 'mrl_memory', 'endpoint': '/search', 'data': {'query': 'test'}},
    {'name': 'llm', 'service': 'llm_routing', 'endpoint': '/route', 'data': {'prompt': 'test'}}
]
results = parallel_mcp_calls(calls)
```

---

## 実践例

### 例1: インテリジェントコード補完

```python
class CodeCompletionSkill:
    """コンテキストを考慮したコード補完スキル"""
    
    def complete_code(self, partial_code: str, context: dict):
        # 1. MRL Memoryから関連するコード履歴を取得
        memory_url = f"{get_service_url('mrl_memory')}/search"
        memories = requests.post(memory_url, json={
            'query': partial_code,
            'context': 'code_history',
            'limit': 5
        }).json()
        
        # 2. LLM Routingで最適なモデルを選択
        routing_url = f"{get_service_url('llm_routing')}/route"
        model_info = requests.post(routing_url, json={
            'prompt': partial_code,
            'difficulty': 'moderate',
            'context': {'memories': memories}
        }).json()
        
        # 3. 選択されたモデルで補完生成
        completion_url = f"{get_service_url('unified_api')}/complete"
        result = requests.post(completion_url, json={
            'code': partial_code,
            'model': model_info['model'],
            'context': context,
            'memories': memories
        }).json()
        
        # 4. 成功した補完をメモリに保存
        if result['success']:
            store_url = f"{get_service_url('mrl_memory')}/store"
            requests.post(store_url, json={
                'content': result['completion'],
                'context': 'code_history',
                'tags': ['completion', 'successful']
            })
        
        return result
```

### 例2: 包括的プロジェクト分析

```python
class ProjectAnalysisSkill:
    """プロジェクト全体を分析するスキル"""
    
    def analyze_project(self, project_path: str):
        # 並列で複数の分析を実行
        analyses = parallel_mcp_calls([
            {
                'name': 'code_quality',
                'service': 'unified_api',
                'endpoint': '/analyze/quality',
                'data': {'path': project_path}
            },
            {
                'name': 'dependencies',
                'service': 'unified_api',
                'endpoint': '/analyze/dependencies',
                'data': {'path': project_path}
            },
            {
                'name': 'test_coverage',
                'service': 'unified_api',
                'endpoint': '/analyze/tests',
                'data': {'path': project_path}
            }
        ])
        
        # 結果を統合
        report = {
            'quality_score': analyses['code_quality'].get('score', 0),
            'dependencies': analyses['dependencies'].get('packages', []),
            'test_coverage': analyses['test_coverage'].get('coverage', 0),
            'recommendations': []
        }
        
        # LLMで改善提案を生成
        llm_url = f"{get_service_url('llm_routing')}/generate"
        recommendations = requests.post(llm_url, json={
            'prompt': f"プロジェクト分析結果から改善提案:\n{analyses}",
            'model': 'auto'
        }).json()
        
        report['recommendations'] = recommendations['suggestions']
        
        # レポートをメモリに保存
        memory_url = f"{get_service_url('mrl_memory')}/store"
        requests.post(memory_url, json={
            'content': report,
            'context': 'project_analysis',
            'tags': ['analysis', project_path]
        })
        
        return report
```

### 例3: マルチモーダルコンテンツ生成

```python
class ContentGenerationSkill:
    """テキスト → 画像 → 動画のマルチモーダル生成"""
    
    def generate_content(self, description: str):
        # チェーン実行
        operations = [
            {
                'service': 'llm_routing',
                'endpoint': '/enhance_prompt',
                'data': {'prompt': description}
            },
            {
                'service': 'unified_api',
                'endpoint': '/generate_image',
                'data': {}  # 前の結果から自動設定
            },
            {
                'service': 'video_pipeline',
                'endpoint': '/create_video',
                'data': {'style': 'cinematic'}
            }
        ]
        
        final_result = chain_mcp_calls(operations)
        
        # ギャラリーに保存
        gallery_url = f"{get_service_url('gallery_api')}/save"
        requests.post(gallery_url, json={
            'image': final_result.get('image_path'),
            'video': final_result.get('video_path'),
            'description': description,
            'tags': ['generated', 'multimodal']
        })
        
        return final_result
```

---

## デバッグとテスト

### スキルのテスト

```python
# test_skills.py
import unittest
from skills.my_skill.main import create_skill

class TestMySkill(unittest.TestCase):
    def setUp(self):
        self.skill = create_skill()
    
    def test_execute_success(self):
        params = {
            'input_data': 'test',
            'options': {}
        }
        result = self.skill.execute(params)
        self.assertTrue(result['success'])
    
    def test_validate_params(self):
        invalid_params = {'input_data': 'test'}
        self.assertFalse(self.skill.validate_params(invalid_params))

if __name__ == '__main__':
    unittest.main()
```

### スキルのロギング

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/skills.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('MySkill')

class MySkill:
    def execute(self, params):
        logger.info(f"Executing skill with params: {params}")
        try:
            result = self._process(params)
            logger.info(f"Skill execution successful: {result}")
            return result
        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            raise
```

---

## 関連リンク

- [スニペットガイド](./SNIPPETS_GUIDE.md)
- [MCPサーバーガイド](./MCP_SERVERS_GUIDE.md)
- [起動依存関係](./STARTUP_DEPENDENCY.md)
