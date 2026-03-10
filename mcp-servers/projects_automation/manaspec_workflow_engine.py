#!/usr/bin/env python3
"""
ManaSpec Workflow Engine
OPENSPEC Proposal→Apply→Archive の自動化エンジン

Remi: Proposal生成・レビュー
Luna: Apply実行・実装
Mina: Archive管理・学習
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import aiohttp

class ManaSpecWorkflowEngine:
    """ManaSpec ワークフローエンジン"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.openspec_dir = self.project_path / "openspec"
        self.changes_dir = self.openspec_dir / "changes"
        self.specs_dir = self.openspec_dir / "specs"
        self.archive_dir = self.changes_dir / "archive"
        
        # ManaOS API endpoints
        self.remi_url = os.getenv("REMI_URL", "http://localhost:9200/orchestrate")
        self.luna_url = os.getenv("LUNA_URL", "http://localhost:9203/actuate")
        self.mina_url = os.getenv("MINA_URL", "http://localhost:9205/ingest")
        
        # Workflow state
        self.current_phase = None
        self.change_id = None
        self.workflow_history = []
    
    async def run_openspec_cmd(self, cmd: str) -> tuple[int, str, str]:
        """Run openspec command asynchronously"""
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_path)
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(), stderr.decode()  # type: ignore
    
    async def call_mrl_api(self, url: str, data: Dict, actor: str) -> Optional[Dict]:
        """Call MRL API asynchronously"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=30) as response:  # type: ignore
                    if response.status == 200:
                        result = await response.json()
                        self.log_event(f"{actor}_api_call", {"request": data, "response": result})
                        return result
                    else:
                        self.log_event(f"{actor}_api_error", {"status": response.status})
                        return None
        except aiohttp.ClientConnectorError:
            self.log_event(f"{actor}_offline", {})
            return None
        except Exception as e:
            self.log_event(f"{actor}_error", {"error": str(e)})
            return None
    
    def log_event(self, event_type: str, data: Dict):
        """Log workflow event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
            "change_id": self.change_id,
            "phase": self.current_phase
        }
        self.workflow_history.append(event)
        print(f"[LOG] {event_type}: {json.dumps(data, ensure_ascii=False)[:100]}")
    
    async def phase_1_proposal(self, feature_description: str, change_id: Optional[str] = None) -> str:
        """
        Phase 1: Proposal Creation with Remi
        
        Remiが機能の提案を分析し、適切なchange構造を提案する
        """
        self.current_phase = "proposal"
        
        if not change_id:
            # Generate change-id from feature description
            change_id = self._generate_change_id(feature_description)
        
        self.change_id = change_id
        self.log_event("phase_1_start", {"feature": feature_description, "change_id": change_id})
        
        # Step 1: Ask Remi for guidance
        remi_request = {
            "text": f"""OpenSpec Change Proposalを作成します。

機能: {feature_description}

以下を提案してください：
1. 適切なchange-id（kebab-case, verb-led）
2. 影響を受けるcapabilities
3. 必要なrequirementsとscenarios
4. implementation tasksのリスト
5. 技術的な考慮事項

JSON形式で回答してください。
""",
            "actor": "remi",
            "context": {
                "task": "openspec_proposal_generation",
                "project_path": str(self.project_path)
            }
        }
        
        remi_response = await self.call_mrl_api(self.remi_url, remi_request, "remi")
        
        if not remi_response:
            print("⚠️ Remi offline - generating proposal without AI assistance")
            proposal_data = self._generate_basic_proposal(feature_description, change_id)
        else:
            proposal_data = self._parse_remi_proposal(remi_response, feature_description, change_id)
        
        # Step 2: Create proposal structure
        change_path = self.changes_dir / change_id
        change_path.mkdir(parents=True, exist_ok=True)
        
        # Create proposal.md
        proposal_md = self._create_proposal_md(proposal_data)
        (change_path / "proposal.md").write_text(proposal_md)
        
        # Create tasks.md
        tasks_md = self._create_tasks_md(proposal_data)
        (change_path / "tasks.md").write_text(tasks_md)
        
        # Create spec deltas
        for capability in proposal_data.get("capabilities", []):
            spec_path = change_path / "specs" / capability["name"]
            spec_path.mkdir(parents=True, exist_ok=True)
            spec_md = self._create_spec_delta(capability)
            (spec_path / "spec.md").write_text(spec_md)
        
        # Step 3: Validate
        returncode, stdout, stderr = await self.run_openspec_cmd(f"openspec validate {change_id} --strict")
        
        if returncode == 0:
            self.log_event("validation_success", {"change_id": change_id})
            print(f"✅ Proposal作成完了: {change_id}")
            print(f"📁 場所: {change_path}")
        else:
            self.log_event("validation_failed", {"error": stderr})
            print(f"❌ Validation失敗:\n{stderr}")
            return None  # type: ignore
        
        return change_id
    
    async def phase_2_apply(self, change_id: str, auto_implement: bool = False) -> bool:
        """
        Phase 2: Implementation with Luna
        
        Lunaが実装を実行する
        """
        self.current_phase = "apply"
        self.change_id = change_id
        self.log_event("phase_2_start", {"change_id": change_id})
        
        # Step 1: Load change details
        change_path = self.changes_dir / change_id
        if not change_path.exists():
            print(f"❌ Change not found: {change_id}")
            return False
        
        proposal = (change_path / "proposal.md").read_text()
        tasks = (change_path / "tasks.md").read_text()
        
        # Step 2: Validate before implementation
        returncode, stdout, stderr = await self.run_openspec_cmd(f"openspec validate {change_id} --strict")
        
        if returncode != 0:
            print(f"❌ Validation failed:\n{stderr}")
            return False
        
        print(f"✅ Validation成功: {change_id}")
        
        # Step 3: Notify Luna for implementation
        luna_request = {
            "action": "implement_openspec_change",
            "change_id": change_id,
            "proposal": proposal,
            "tasks": tasks,
            "auto_implement": auto_implement,
            "context": {
                "project_path": str(self.project_path),
                "change_path": str(change_path)
            }
        }
        
        luna_response = await self.call_mrl_api(self.luna_url, luna_request, "luna")
        
        if luna_response:
            print(f"✅ Luna実装開始: {change_id}")
            self.log_event("implementation_started", {
                "change_id": change_id,
                "luna_response": luna_response
            })
            
            if auto_implement:
                # Wait for Luna to complete (in real scenario, this would be async)
                print("⏳ Lunaによる自動実装を待機中...")
                # In production, this would poll Luna's status endpoint
        else:
            print("⚠️ Luna offline - manual implementation required")
            print(f"📋 Tasks to complete:\n{tasks}")
        
        return True
    
    async def phase_3_archive(self, change_id: str, skip_confirmation: bool = False) -> bool:
        """
        Phase 3: Archive with Mina
        
        Minaが完了した変更をアーカイブし、学習データとして保存する
        """
        self.current_phase = "archive"
        self.change_id = change_id
        self.log_event("phase_3_start", {"change_id": change_id})
        
        # Step 1: Archive with openspec
        cmd = f"openspec archive {change_id}"
        if skip_confirmation:
            cmd += " --yes"
        
        returncode, stdout, stderr = await self.run_openspec_cmd(cmd)
        
        if returncode != 0:
            print(f"❌ Archive failed:\n{stderr}")
            return False
        
        print(f"✅ Archive成功: {change_id}")
        print(stdout)
        
        # Step 2: Extract archive data for Mina
        archive_date = datetime.now().strftime("%Y-%m-%d")
        archived_path = self.archive_dir / f"{archive_date}-{change_id}"
        
        if archived_path.exists():
            # Collect all files for learning
            archive_data = {
                "change_id": change_id,
                "archive_date": archive_date,
                "proposal": (archived_path / "proposal.md").read_text() if (archived_path / "proposal.md").exists() else "",
                "tasks": (archived_path / "tasks.md").read_text() if (archived_path / "tasks.md").exists() else "",
                "specs": [],
                "archive_output": stdout
            }
            
            # Collect spec deltas
            specs_path = archived_path / "specs"
            if specs_path.exists():
                for capability_dir in specs_path.iterdir():
                    if capability_dir.is_dir():
                        spec_file = capability_dir / "spec.md"
                        if spec_file.exists():
                            archive_data["specs"].append({
                                "capability": capability_dir.name,
                                "content": spec_file.read_text()
                            })
            
            # Step 3: Send to Mina for learning
            mina_request = {
                "event_type": "openspec_change_archived",
                "data": archive_data
            }
            
            mina_response = await self.call_mrl_api(self.mina_url, mina_request, "mina")
            
            if mina_response:
                print("✅ Minaに学習データを保存しました")
                self.log_event("learning_saved", {"change_id": change_id})
            else:
                print("⚠️ Mina offline - learning data not saved")
        
        # Step 4: Save workflow history
        self._save_workflow_history(change_id)
        
        return True
    
    async def auto_workflow(self, feature_description: str, auto_implement: bool = False) -> bool:
        """
        Complete automated workflow: Proposal → Apply → Archive
        
        完全自動化されたワークフロー
        """
        print(f"\n{'='*60}")
        print("🚀 ManaSpec 自動ワークフロー開始")
        print(f"{'='*60}\n")
        
        # Phase 1: Proposal
        print("\n📋 Phase 1: Proposal Generation (Remi)")
        change_id = await self.phase_1_proposal(feature_description)
        
        if not change_id:
            print("❌ Proposal生成失敗")
            return False
        
        # Phase 2: Apply
        print("\n⚙️ Phase 2: Implementation (Luna)")
        success = await self.phase_2_apply(change_id, auto_implement)
        
        if not success:
            print("❌ 実装フェーズ失敗")
            return False
        
        if not auto_implement:
            print("\n⏸️  手動実装が必要です")
            print("実装完了後、次のコマンドを実行してください:")
            print(f"  manaspec archive {change_id} --yes")
            return True
        
        # Phase 3: Archive
        print("\n📦 Phase 3: Archive (Mina)")
        success = await self.phase_3_archive(change_id, skip_confirmation=True)
        
        if not success:
            print("❌ アーカイブ失敗")
            return False
        
        print(f"\n{'='*60}")
        print(f"✅ ワークフロー完了: {change_id}")
        print(f"{'='*60}\n")
        
        return True
    
    def _generate_change_id(self, feature: str) -> str:
        """Generate kebab-case change-id from feature description"""
        import re
        # Simple implementation - can be enhanced with NLP
        words = re.findall(r'\w+', feature.lower())
        if words[0] not in ['add', 'update', 'remove', 'refactor', 'fix']:
            words.insert(0, 'add')
        return '-'.join(words[:5])  # Limit to 5 words
    
    def _generate_basic_proposal(self, feature: str, change_id: str) -> Dict:
        """Generate basic proposal without AI"""
        return {
            "change_id": change_id,
            "feature": feature,
            "capabilities": [
                {
                    "name": change_id.split('-', 1)[1] if '-' in change_id else change_id,
                    "requirements": [
                        {
                            "name": f"Basic {feature}",
                            "description": f"The system SHALL provide {feature}",
                            "scenarios": [
                                {
                                    "name": "Success case",
                                    "when": "user requests the feature",
                                    "then": "system provides the expected result"
                                }
                            ]
                        }
                    ]
                }
            ],
            "tasks": [
                "Implement core functionality",
                "Add tests",
                "Update documentation"
            ]
        }
    
    def _parse_remi_proposal(self, remi_response: Dict, feature: str, change_id: str) -> Dict:
        """Parse Remi's response into proposal structure"""
        # Try to parse JSON from Remi's response
        result = remi_response.get("result", "{}")
        
        try:
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result
            
            # Use Remi's suggestion or fallback
            return {
                "change_id": data.get("change_id", change_id),
                "feature": feature,
                "capabilities": data.get("capabilities", []),
                "tasks": data.get("tasks", [])
            }
        except json.JSONDecodeError:
            # Fallback to basic proposal
            return self._generate_basic_proposal(feature, change_id)
    
    def _create_proposal_md(self, data: Dict) -> str:
        """Create proposal.md content"""
        capabilities = ', '.join([c['name'] for c in data.get('capabilities', [])])
        
        return f"""## Why
{data['feature']}

## What Changes
- Implement {data['feature']}
- Add necessary tests and documentation

## Impact
- Affected specs: {capabilities}
- Affected code: New implementation
- Breaking changes: None
"""
    
    def _create_tasks_md(self, data: Dict) -> str:
        """Create tasks.md content"""
        tasks = data.get('tasks', [])
        
        content = "## 1. Implementation\n"
        for i, task in enumerate(tasks, 1):
            content += f"- [ ] 1.{i} {task}\n"
        
        return content
    
    def _create_spec_delta(self, capability: Dict) -> str:
        """Create spec delta content"""
        content = "## ADDED Requirements\n\n"
        
        for req in capability.get('requirements', []):
            content += f"### Requirement: {req['name']}\n"
            content += f"{req['description']}\n\n"
            
            for scenario in req.get('scenarios', []):
                content += f"#### Scenario: {scenario['name']}\n"
                content += f"- **WHEN** {scenario['when']}\n"
                content += f"- **THEN** {scenario['then']}\n\n"
        
        return content
    
    def _save_workflow_history(self, change_id: str):
        """Save workflow history to file"""
        history_path = self.archive_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{change_id}" / "workflow_history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(self.workflow_history, indent=2, ensure_ascii=False))
        print(f"📊 ワークフロー履歴保存: {history_path}")


async def main():
    """CLI entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: manaspec_workflow_engine.py <feature_description>")
        sys.exit(1)
    
    feature = ' '.join(sys.argv[1:])
    
    engine = ManaSpecWorkflowEngine()
    success = await engine.auto_workflow(feature, auto_implement=False)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())

