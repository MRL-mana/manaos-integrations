#!/usr/bin/env python3
"""
ManaSpec Multi-Project Manager
複数のOpenSpecプロジェクトを一元管理
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import subprocess

class ManaSpecMultiProject:
    """マルチプロジェクト管理"""
    
    def __init__(self, config_file: str = "~/.manaspec/projects.json"):
        self.config_file = Path(config_file).expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.projects = self.load_projects()
    
    def load_projects(self) -> Dict:
        """プロジェクト設定をロード"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_projects(self):
        """プロジェクト設定を保存"""
        with open(self.config_file, 'w') as f:
            json.dump(self.projects, f, indent=2)
    
    def add_project(self, name: str, path: str, description: str = ""):
        """プロジェクトを追加"""
        path = Path(path).resolve()
        
        if not (path / "openspec").exists():
            print(f"❌ Not a valid OpenSpec project: {path}")
            return False
        
        self.projects[name] = {
            "path": str(path),
            "description": description,
            "added_at": datetime.now().isoformat()
        }
        
        self.save_projects()
        print(f"✅ Project added: {name} -> {path}")
        return True
    
    def remove_project(self, name: str):
        """プロジェクトを削除"""
        if name in self.projects:
            del self.projects[name]
            self.save_projects()
            print(f"✅ Project removed: {name}")
            return True
        else:
            print(f"❌ Project not found: {name}")
            return False
    
    def list_projects(self):
        """プロジェクト一覧を表示"""
        if not self.projects:
            print("📂 No projects registered")
            return
        
        print("\n📂 Registered Projects:\n")
        for name, info in self.projects.items():
            print(f"  {name}")
            print(f"    Path: {info['path']}")
            if info.get('description'):
                print(f"    Description: {info['description']}")
            print()
    
    def get_project_status(self, name: str) -> Dict:
        """プロジェクトのステータス取得"""
        if name not in self.projects:
            return {"error": "Project not found"}
        
        project_path = self.projects[name]["path"]
        
        # OpenSpec コマンド実行
        try:
            # Changes
            result = subprocess.run(
                ["openspec", "list"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            changes_output = result.stdout
            
            # Specs
            result = subprocess.run(
                ["openspec", "list", "--specs"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            specs_output = result.stdout
            
            return {
                "name": name,
                "path": project_path,
                "changes": changes_output,
                "specs": specs_output
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_status(self) -> List[Dict]:
        """全プロジェクトのステータス取得"""
        statuses = []
        for name in self.projects.keys():
            status = self.get_project_status(name)
            statuses.append(status)
        return statuses
    
    def run_command(self, project_name: str, command: str):
        """指定プロジェクトでコマンド実行"""
        if project_name not in self.projects:
            print(f"❌ Project not found: {project_name}")
            return False
        
        project_path = self.projects[project_name]["path"]
        
        print(f"📂 Running in {project_name}: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def validate_all(self):
        """全プロジェクトのvalidation"""
        print("\n🔍 Validating all projects...\n")
        
        results = {}
        for name, info in self.projects.items():
            print(f"Validating {name}...")
            success = self.run_command(name, "openspec validate --strict")
            results[name] = "✅ Pass" if success else "❌ Fail"
        
        print("\n📊 Validation Results:\n")
        for name, result in results.items():
            print(f"  {name}: {result}")
    
    def sync_all(self):
        """全プロジェクトを同期"""
        print("\n🔄 Syncing all projects...\n")
        
        for name in self.projects.keys():
            print(f"Syncing {name}...")
            # Git pull
            self.run_command(name, "git pull")
            # OpenSpec update
            self.run_command(name, "openspec update")


def main():
    """CLI entry point"""
    import sys
    
    manager = ManaSpecMultiProject()
    
    if len(sys.argv) < 2:
        print("Usage: manaspec-multi <command> [args]")
        print("\nCommands:")
        print("  add <name> <path> [description]  - Add a project")
        print("  remove <name>                     - Remove a project")
        print("  list                              - List all projects")
        print("  status [name]                     - Show project status")
        print("  run <name> <command>              - Run command in project")
        print("  validate-all                      - Validate all projects")
        print("  sync-all                          - Sync all projects")
        return
    
    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 4:
            print("Usage: manaspec-multi add <name> <path> [description]")
            return
        name = sys.argv[2]
        path = sys.argv[3]
        description = sys.argv[4] if len(sys.argv) > 4 else ""
        manager.add_project(name, path, description)
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: manaspec-multi remove <name>")
            return
        manager.remove_project(sys.argv[2])
    
    elif command == "list":
        manager.list_projects()
    
    elif command == "status":
        if len(sys.argv) < 3:
            # All projects
            statuses = manager.get_all_status()
            for status in statuses:
                print(f"\n📂 {status.get('name', 'Unknown')}")
                print(f"Path: {status.get('path', 'N/A')}")
                if 'error' in status:
                    print(f"❌ Error: {status['error']}")
                else:
                    print(status.get('changes', 'No changes'))
                    print(status.get('specs', 'No specs'))
        else:
            # Single project
            status = manager.get_project_status(sys.argv[2])
            print(json.dumps(status, indent=2))
    
    elif command == "run":
        if len(sys.argv) < 4:
            print("Usage: manaspec-multi run <name> <command>")
            return
        name = sys.argv[2]
        cmd = ' '.join(sys.argv[3:])
        manager.run_command(name, cmd)
    
    elif command == "validate-all":
        manager.validate_all()
    
    elif command == "sync-all":
        manager.sync_all()
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == '__main__':
    main()

