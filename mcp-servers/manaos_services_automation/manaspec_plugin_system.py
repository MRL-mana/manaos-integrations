#!/usr/bin/env python3
"""
ManaSpec Plugin System
拡張可能なプラグインエコシステム
"""

import os
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Callable
from abc import ABC, abstractmethod

class ManaSpecPlugin(ABC):
    """プラグインの基底クラス"""
    
    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名を返す"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """バージョンを返す"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]):
        """プラグインを初期化"""
        pass
    
    def on_proposal_created(self, change_id: str, proposal: Dict):
        """Proposal作成時のフック"""
        pass
    
    def on_proposal_validated(self, change_id: str, result: Dict):
        """Validation完了時のフック"""
        pass
    
    def on_apply_started(self, change_id: str):
        """Apply開始時のフック"""
        pass
    
    def on_apply_completed(self, change_id: str, result: Dict):
        """Apply完了時のフック"""
        pass
    
    def on_archive_created(self, change_id: str, archive_path: str):
        """Archive作成時のフック"""
        pass


class PluginManager:
    """プラグイン管理"""
    
    def __init__(self, plugin_dir: str = "~/.manaspec/plugins"):
        self.plugin_dir = Path(plugin_dir).expanduser()
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, ManaSpecPlugin] = {}
        self.hooks: Dict[str, List[Callable]] = {
            'on_proposal_created': [],
            'on_proposal_validated': [],
            'on_apply_started': [],
            'on_apply_completed': [],
            'on_archive_created': []
        }
    
    def load_plugin(self, plugin_path: str) -> bool:
        """プラグインをロード"""
        try:
            plugin_path = Path(plugin_path)  # type: ignore
            
            # プラグインモジュールをロード
            spec = importlib.util.spec_from_file_location(
                plugin_path.stem,  # type: ignore
                plugin_path
            )
            module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            
            # プラグインクラスを探す
            for item_name in dir(module):
                item = getattr(module, item_name)
                if isinstance(item, type) and issubclass(item, ManaSpecPlugin) and item != ManaSpecPlugin:
                    # インスタンス化
                    plugin = item()
                    plugin_name = plugin.get_name()
                    
                    # 初期化
                    plugin.initialize({'plugin_dir': str(self.plugin_dir)})
                    
                    # 登録
                    self.plugins[plugin_name] = plugin
                    
                    # フック登録
                    for hook_name in self.hooks.keys():
                        hook_method = getattr(plugin, hook_name, None)
                        if hook_method and callable(hook_method):
                            self.hooks[hook_name].append(hook_method)
                    
                    print(f"✅ Plugin loaded: {plugin_name} v{plugin.get_version()}")
                    return True
            
            print(f"⚠️ No plugin class found in {plugin_path}")
            return False
            
        except Exception as e:
            print(f"❌ Failed to load plugin {plugin_path}: {e}")
            return False
    
    def load_all_plugins(self):
        """全プラグインをロード"""
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            self.load_plugin(str(plugin_file))
    
    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """フックを実行"""
        if hook_name not in self.hooks:
            return
        
        for hook_func in self.hooks[hook_name]:
            try:
                hook_func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ Hook {hook_name} failed: {e}")
    
    def list_plugins(self):
        """プラグイン一覧"""
        if not self.plugins:
            print("No plugins loaded")
            return
        
        print("\n📦 Loaded Plugins:\n")
        for name, plugin in self.plugins.items():
            print(f"  {name} v{plugin.get_version()}")
    
    def unload_plugin(self, plugin_name: str):
        """プラグインをアンロード"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            
            # フックから削除
            for hook_name in self.hooks.keys():
                hook_method = getattr(plugin, hook_name, None)
                if hook_method in self.hooks[hook_name]:
                    self.hooks[hook_name].remove(hook_method)  # type: ignore
            
            del self.plugins[plugin_name]
            print(f"✅ Plugin unloaded: {plugin_name}")
            return True
        else:
            print(f"❌ Plugin not found: {plugin_name}")
            return False


# ========== サンプルプラグイン ==========

class SlackNotificationPlugin(ManaSpecPlugin):
    """Slack通知プラグイン"""
    
    def get_name(self) -> str:
        return "slack-notification"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, context: Dict[str, Any]):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        print(f"  Slack Webhook: {'configured' if self.webhook_url else 'not configured'}")
    
    def on_proposal_created(self, change_id: str, proposal: Dict):
        print(f"  📋 Slack: New proposal created - {change_id}")
        # 実際のSlack通知はここで実装
        # requests.post(self.webhook_url, json={...})
    
    def on_archive_created(self, change_id: str, archive_path: str):
        print(f"  📦 Slack: Archived - {change_id}")


class AIReviewPlugin(ManaSpecPlugin):
    """AI自動レビュープラグイン"""
    
    def get_name(self) -> str:
        return "ai-review"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, context: Dict[str, Any]):
        self.context = context
        print("  AI Review Plugin initialized")
    
    def on_proposal_validated(self, change_id: str, result: Dict):
        print(f"  🤖 AI Review: Analyzing proposal - {change_id}")
        # GPT-4/Claude等でProposalをレビュー
        # suggestions = ai_review_proposal(change_id)


class MetricsCollectorPlugin(ManaSpecPlugin):
    """メトリクス収集プラグイン"""
    
    def get_name(self) -> str:
        return "metrics-collector"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, context: Dict[str, Any]):
        self.metrics_file = Path(context['plugin_dir']) / "metrics.json"
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> Dict:
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        return {"proposals": 0, "archives": 0, "validations": 0}
    
    def _save_metrics(self):
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def on_proposal_created(self, change_id: str, proposal: Dict):
        self.metrics["proposals"] += 1
        self._save_metrics()
        print(f"  📊 Metrics: Total proposals = {self.metrics['proposals']}")
    
    def on_proposal_validated(self, change_id: str, result: Dict):
        self.metrics["validations"] += 1
        self._save_metrics()
    
    def on_archive_created(self, change_id: str, archive_path: str):
        self.metrics["archives"] += 1
        self._save_metrics()
        print(f"  📊 Metrics: Total archives = {self.metrics['archives']}")


def create_plugin_template(plugin_name: str, output_path: str = None):  # type: ignore
    """プラグインテンプレートを作成"""
    if output_path is None:
        output_path = f"~/.manaspec/plugins/{plugin_name}.py"
    
    output_path = Path(output_path).expanduser()  # type: ignore
    output_path.parent.mkdir(parents=True, exist_ok=True)  # type: ignore
    
    template = f'''#!/usr/bin/env python3
"""
ManaSpec Plugin: {plugin_name}
"""

from manaspec_plugin_system import ManaSpecPlugin
from typing import Dict, Any

class {plugin_name.title().replace('-', '')}Plugin(ManaSpecPlugin):
    """TODO: プラグインの説明"""
    
    def get_name(self) -> str:
        return "{plugin_name}"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, context: Dict[str, Any]):
        """初期化処理"""
        self.context = context
        print(f"  {{self.get_name()}} initialized")
    
    def on_proposal_created(self, change_id: str, proposal: Dict):
        """Proposal作成時"""
        print(f"  {{self.get_name()}}: Proposal created - {{change_id}}")
        # TODO: 実装
    
    def on_archive_created(self, change_id: str, archive_path: str):
        """Archive作成時"""
        print(f"  {{self.get_name()}}: Archived - {{change_id}}")
        # TODO: 実装
'''
    
    output_path.write_text(template)  # type: ignore
    print(f"✅ Plugin template created: {output_path}")


def main():
    """デモ"""
    print("🔌 ManaSpec Plugin System Demo\n")
    
    manager = PluginManager()
    
    # サンプルプラグインを登録
    # (実際は外部ファイルからロードするが、デモ用に直接登録)
    manager.plugins["slack"] = SlackNotificationPlugin()
    manager.plugins["slack"].initialize({'plugin_dir': str(manager.plugin_dir)})
    
    manager.plugins["ai-review"] = AIReviewPlugin()
    manager.plugins["ai-review"].initialize({'plugin_dir': str(manager.plugin_dir)})
    
    manager.plugins["metrics"] = MetricsCollectorPlugin()
    manager.plugins["metrics"].initialize({'plugin_dir': str(manager.plugin_dir)})
    
    # フック登録
    for plugin in manager.plugins.values():
        for hook_name in manager.hooks.keys():
            hook_method = getattr(plugin, hook_name, None)
            if hook_method and callable(hook_method):
                manager.hooks[hook_name].append(hook_method)
    
    manager.list_plugins()
    
    # フックをテスト
    print("\n🧪 Testing hooks...\n")
    
    manager.trigger_hook('on_proposal_created', 'add-test-feature', {'title': 'Test'})
    manager.trigger_hook('on_proposal_validated', 'add-test-feature', {'valid': True})
    manager.trigger_hook('on_archive_created', 'add-test-feature', '/path/to/archive')
    
    print("\n✅ Plugin system working!")


if __name__ == '__main__':
    main()

