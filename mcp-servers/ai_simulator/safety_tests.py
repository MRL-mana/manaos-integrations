"""
AI Simulator Safety Framework Tests
安全フレームワークのテスト
"""

import unittest
import time
import tempfile
import os
from unittest.mock import Mock, patch

# テスト対象モジュール
from sandbox.security_policy import SecurityManager, SecurityPolicy, ResourceLimits
from sandbox.container_manager import ContainerManager
from monitoring.resource_monitor import ResourceMonitor, AlertRule
from monitoring.alert_system import AlertSystem, NotificationConfig

class TestSecurityPolicy(unittest.TestCase):
    """セキュリティポリシーのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.policy = SecurityPolicy(
            allowed_directories=['/app/workspace', '/tmp'],
            blocked_commands=['rm -rf /', 'sudo'],
            max_execution_time=60
        )
        
        self.limits = ResourceLimits(
            max_memory_mb=256,
            max_cpu_percent=50.0,
            max_processes=5
        )
        
        self.security_manager = SecurityManager(self.policy, self.limits)
    
    def test_file_access_allowed(self):
        """許可されたファイルアクセステスト"""
        self.assertTrue(self.security_manager.check_file_access('/app/workspace/test.txt'))
        self.assertTrue(self.security_manager.check_file_access('/tmp/test.txt'))
    
    def test_file_access_blocked(self):
        """ブロックされたファイルアクセステスト"""
        self.assertFalse(self.security_manager.check_file_access('/etc/passwd'))
        self.assertFalse(self.security_manager.check_file_access('/root/secret.txt'))
    
    def test_execution_time_check(self):
        """実行時間チェックテスト"""
        # 初期状態では制限内
        self.assertTrue(self.security_manager.check_execution_time())
        
        # 時間を進める
        with patch('time.time', return_value=time.time() + 70):
            self.assertFalse(self.security_manager.check_execution_time())

class TestResourceMonitor(unittest.TestCase):
    """リソースモニターのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.monitor = ResourceMonitor(check_interval=0.1)
    
    def test_metrics_collection(self):
        """メトリクス収集テスト"""
        metrics = self.monitor.collect_metrics()
        
        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertLessEqual(metrics.memory_percent, 100)
        self.assertGreaterEqual(metrics.process_count, 0)
    
    def test_alert_rule_creation(self):
        """アラートルール作成テスト"""
        rule = AlertRule(
            name="Test Rule",
            metric="cpu_percent",
            threshold=80.0,
            operator=">",
            severity="warning"
        )
        
        self.monitor.add_alert_rule(rule)
        self.assertIn(rule, self.monitor.alert_rules)
    
    def test_alert_triggering(self):
        """アラート発火テスト"""
        # 高CPU使用率のメトリクスを作成
        metrics = self.monitor.collect_metrics()
        metrics.cpu_percent = 90.0  # 閾値を超える値
        
        # アラートコールバック設定
        alert_triggered = []
        def alert_callback(alert_data):
            alert_triggered.append(alert_data)
        
        self.monitor.add_alert_callback(alert_callback)
        
        # アラートチェック実行
        self.monitor.check_alerts(metrics)
        
        # アラートが発火したかチェック
        self.assertGreater(len(alert_triggered), 0)

class TestAlertSystem(unittest.TestCase):
    """アラートシステムのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        config = NotificationConfig(
            email_enabled=False,
            webhook_enabled=False,
            log_enabled=True
        )
        self.alert_system = AlertSystem(config)
    
    def test_alert_creation(self):
        """アラート作成テスト"""
        alert_id = self.alert_system.create_alert(
            "Test Rule",
            "warning",
            "Test message"
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIn(alert_id, self.alert_system.active_alerts)
    
    def test_alert_resolution(self):
        """アラート解決テスト"""
        alert_id = self.alert_system.create_alert(
            "Test Rule",
            "warning",
            "Test message"
        )
        
        # アラート解決
        result = self.alert_system.resolve_alert(alert_id)
        self.assertTrue(result)
        self.assertNotIn(alert_id, self.alert_system.active_alerts)
    
    def test_alert_statistics(self):
        """アラート統計テスト"""
        # 複数のアラート作成
        self.alert_system.create_alert("Rule1", "warning", "Message1")
        self.alert_system.create_alert("Rule2", "critical", "Message2")
        
        stats = self.alert_system.get_alert_statistics()
        
        self.assertEqual(stats['total_alerts'], 2)
        self.assertEqual(stats['active_alerts'], 2)
        self.assertEqual(stats['resolved_alerts'], 0)
        self.assertIn('warning', stats['severity_breakdown'])
        self.assertIn('critical', stats['severity_breakdown'])

class TestContainerManager(unittest.TestCase):
    """コンテナマネージャーのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.container_manager = ContainerManager()
    
    @patch('docker.from_env')
    def test_container_creation(self, mock_docker):
        """コンテナ作成テスト"""
        # Dockerクライアントのモック
        mock_client = Mock()
        mock_container = Mock()
        mock_container.short_id = "test123"
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client
        
        container_id = self.container_manager.create_sandbox_container()
        
        self.assertEqual(container_id, "test123")
        self.assertIn("test123", self.container_manager.containers)
    
    def test_container_listing(self):
        """コンテナ一覧テスト"""
        # モックコンテナ追加
        mock_container = Mock()
        mock_container.short_id = "test123"
        self.container_manager.containers["test123"] = mock_container
        
        containers = self.container_manager.list_containers()
        
        self.assertIn("test123", containers)

class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        # 一時ディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, 'logs'), exist_ok=True)
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_security_framework_integration(self):
        """安全フレームワーク統合テスト"""
        # 設定ファイル作成
        config_path = os.path.join(self.temp_dir, 'test_config.yaml')
        with open(config_path, 'w') as f:
            f.write("""
resource_limits:
  max_memory_mb: 256
  max_cpu_percent: 50.0
  max_execution_time: 60

security_policy:
  allowed_directories: ['/tmp']
  blocked_commands: ['rm -rf /']
  enable_network_isolation: true
  enable_file_monitoring: true

monitoring:
  check_interval: 0.1
  metrics_history_size: 100

alerts:
  rules: []

notifications:
  email:
    enabled: false
  webhook:
    enabled: false
  log:
    enabled: true
            """)
        
        # 安全フレームワーク初期化
        from main import AISimulatorSafetyFramework  # type: ignore[attr-defined]
        
        framework = AISimulatorSafetyFramework(config_path)
        
        # 初期化テスト
        result = framework.initialize()
        self.assertTrue(result)
        
        # 状態取得テスト
        status = framework.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn('is_running', status)
        self.assertIn('components', status)
        
        # クリーンアップ
        framework.stop()

def run_tests():
    """テスト実行"""
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # テストケース追加
    test_suite.addTest(unittest.makeSuite(TestSecurityPolicy))  # type: ignore[attr-defined]
    test_suite.addTest(unittest.makeSuite(TestResourceMonitor))  # type: ignore[attr-defined]
    test_suite.addTest(unittest.makeSuite(TestAlertSystem))  # type: ignore[attr-defined]
    test_suite.addTest(unittest.makeSuite(TestContainerManager))  # type: ignore[attr-defined]
    test_suite.addTest(unittest.makeSuite(TestIntegration))  # type: ignore[attr-defined]
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
        exit(1)