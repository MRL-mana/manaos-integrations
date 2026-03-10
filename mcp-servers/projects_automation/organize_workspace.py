#!/usr/bin/env python3
"""
ManaOS Workspace Organizer
ルートディレクトリのPythonファイルを適切に分類・整理
"""

import shutil
import json
from datetime import datetime
from pathlib import Path

class WorkspaceOrganizer:
    def __init__(self):
        self.root = Path('/root')
        self.organized_dir = self.root / 'organized_workspace'
        
        # カテゴリ別のディレクトリ構造
        self.categories = {
            'manaos': self.organized_dir / 'manaos_core',
            'trinity': self.organized_dir / 'trinity_systems',
            'mcp': self.organized_dir / 'mcp_servers',
            'monitoring': self.organized_dir / 'monitoring_tools',
            'automation': self.organized_dir / 'automation_scripts',
            'dashboard': self.organized_dir / 'dashboards',
            'backup': self.organized_dir / 'backup_systems',
            'ai': self.organized_dir / 'ai_systems',
            'x280': self.organized_dir / 'x280_integration',
            'utils': self.organized_dir / 'utilities',
            'deprecated': self.organized_dir / 'deprecated',
        }
        
        # ファイル分類のキーワード
        self.keywords = {
            'manaos': ['manaos', 'orchestrator', 'actuator', 'intention', 'policy'],
            'trinity': ['trinity', 'secretary', 'google_services'],
            'mcp': ['mcp_server', 'mcp', '_mcp_'],
            'monitoring': ['monitor', 'health', 'metrics', 'alert'],
            'automation': ['auto_', 'scheduler', 'cron', 'launcher'],
            'dashboard': ['dashboard', 'webui', 'interface', 'unified'],
            'backup': ['backup', 'recovery', 'disaster'],
            'ai': ['ai_', 'learning', 'enhancement', 'chatgpt'],
            'x280': ['x280', 'remote_controller'],
            'utils': ['optimizer', 'cleanup', 'helper', 'util'],
        }
        
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'organized': {},
            'skipped': [],
            'errors': []
        }
    
    def create_directories(self):
        """カテゴリディレクトリを作成"""
        for category, path in self.categories.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"📁 作成: {path}")
    
    def classify_file(self, filename: str) -> str:
        """ファイル名からカテゴリを判定"""
        filename_lower = filename.lower()
        
        # キーワードマッチング
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return category
        
        # テストファイル
        if 'test' in filename_lower or 'demo' in filename_lower:
            return 'deprecated'
        
        # デフォルト
        return 'utils'
    
    def get_python_files(self):
        """ルートディレクトリのPythonファイルを取得"""
        return list(self.root.glob('*.py'))
    
    def organize_files(self, dry_run: bool = False):
        """ファイルを整理"""
        python_files = self.get_python_files()
        self.report['total_files'] = len(python_files)
        
        print(f"\n📊 {len(python_files)}個のPythonファイルを処理中...\n")
        
        for file_path in python_files:
            try:
                filename = file_path.name
                
                # 重要ファイルはスキップ
                if filename in ['organize_workspace.py', 'system_optimizer.py', 
                               'auto_health_monitor.py', 'final_optimization_report.py',
                               'screen_sharing_simple.py']:
                    self.report['skipped'].append(filename)
                    continue
                
                # カテゴリ判定
                category = self.classify_file(filename)
                dest_dir = self.categories[category]
                dest_path = dest_dir / filename
                
                # 既に存在する場合はスキップ
                if dest_path.exists():
                    self.report['skipped'].append(f"{filename} (already exists)")
                    continue
                
                # 移動（またはドライラン）
                if not dry_run:
                    shutil.move(str(file_path), str(dest_path))
                
                # レポート記録
                if category not in self.report['organized']:
                    self.report['organized'][category] = []
                self.report['organized'][category].append(filename)
                
                print(f"✅ {filename:50s} → {category}")
                
            except Exception as e:
                error_msg = f"{filename}: {str(e)}"  # type: ignore[possibly-unbound]
                self.report['errors'].append(error_msg)
                print(f"❌ エラー: {error_msg}")
    
    def generate_report(self):
        """レポート生成"""
        report_file = self.root / 'logs' / f'workspace_organization_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 レポート保存: {report_file}")
        return report_file
    
    def print_summary(self):
        """サマリー表示"""
        print("\n" + "="*70)
        print("📊 ワークスペース整理完了")
        print("="*70)
        print(f"\n総ファイル数: {self.report['total_files']}")
        
        organized_count = sum(len(files) for files in self.report['organized'].values())
        print(f"整理済み: {organized_count}")
        print(f"スキップ: {len(self.report['skipped'])}")
        print(f"エラー: {len(self.report['errors'])}")
        
        print("\n📁 カテゴリ別:")
        for category, files in sorted(self.report['organized'].items()):
            print(f"  {category:20s}: {len(files):3d}個")
        
        print("\n" + "="*70 + "\n")

def main():
    import sys
    
    organizer = WorkspaceOrganizer()
    
    # ドライランモード
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("🔍 ドライランモード（実際の移動は行いません）\n")
    
    # ディレクトリ作成
    organizer.create_directories()
    
    # ファイル整理
    organizer.organize_files(dry_run=dry_run)
    
    # レポート生成
    if not dry_run:
        organizer.generate_report()
    
    # サマリー表示
    organizer.print_summary()

if __name__ == '__main__':
    main()

