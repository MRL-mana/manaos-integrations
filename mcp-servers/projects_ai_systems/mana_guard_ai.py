#!/usr/bin/env python3
"""
🤖 Mana Guard AI - 自動セキュリティ監査エージェント
AIによる自己検証・改善提案システム
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import anthropic
import logging

# Trinity統合ヘルパー
sys.path.insert(0, '/root/trinity_workspace/bridge')
try:
    from reflection_helper import log_success, log_failure
    from cognitive_helper import log_agent_event
    TRINITY_ENABLED = True
except ImportError:
    TRINITY_ENABLED = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ManaGuardAI:
    """AI駆動型セキュリティ監査エージェント"""
    
    def __init__(self):
        self.vault_dir = Path('/root/.mana_vault')
        self.report_dir = Path('/root/security_reports')
        self.report_dir.mkdir(exist_ok=True)
        
        self.guard_log = Path('/root/logs/mana_guard.log')
        self.guard_log.parent.mkdir(exist_ok=True)
        
        # Claude APIキーを取得（Vault v2から）
        try:
            from security_vault_v2 import SecurityVaultV2
            vault = SecurityVaultV2()
            self.api_key = vault.get('ANTHROPIC_API_KEY')
            if not self.api_key:
                # フォールバック：環境変数から
                self.api_key = os.getenv('ANTHROPIC_API_KEY')
        except Exception:
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("✅ Mana Guard AI initialized with Claude API")
        else:
            self.client = None
            logger.warning("⚠️ No API key found, running in analysis-only mode")
    
    def run_security_audit(self):
        """セキュリティ監査を実行"""
        logger.info("🔍 Running security audit...")
        
        try:
            result = subprocess.run(
                ['python3', '/root/security_monitor.py'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # 最新のレポートファイルを取得
            report_files = sorted(self.report_dir.glob('security_audit_*.json'), reverse=True)
            if report_files:
                with open(report_files[0], 'r') as f:
                    audit_data = json.load(f)
                return audit_data
            else:
                return {'status': 'no_report', 'issues': []}
        
        except Exception as e:
            logger.error(f"❌ Audit failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def analyze_audit_results(self, audit_data):
        """監査結果をAIで分析"""
        if not self.client:
            logger.warning("⚠️ AI analysis not available (no API key)")
            return self._fallback_analysis(audit_data)
        
        logger.info("🤖 Analyzing audit results with AI...")
        
        # 監査データを整形
        audit_summary = {
            'timestamp': audit_data.get('timestamp', datetime.now().isoformat()),
            'security_score': audit_data.get('security_score', 'unknown'),
            'issues': audit_data.get('issues', []),
            'vault_status': audit_data.get('vault_status', {}),
            'port_status': audit_data.get('port_status', {})
        }
        
        prompt = f"""あなたはMana Guard AI、Manaのセキュリティシステムを守護するAIエージェントです。

以下のセキュリティ監査結果を分析し、改善提案を生成してください：

【監査結果】
{json.dumps(audit_summary, indent=2, ensure_ascii=False)}

【分析タスク】
1. 検出された問題の重要度評価
2. 潜在的なリスクの特定
3. 具体的な改善提案（実装可能なコード付き）
4. 優先度の高い順に3つのアクションアイテム

【出力形式】
JSON形式で以下の構造で返してください：
{{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "日本語での要約",
  "improvements": [
    {{
      "priority": 1,
      "title": "改善項目タイトル",
      "description": "詳細説明",
      "implementation": "実装コード（必要に応じて）",
      "estimated_impact": "期待される効果"
    }}
  ],
  "automated_fixes": [
    {{
      "issue": "問題の説明",
      "fix_command": "自動修復コマンド",
      "requires_approval": true/false
    }}
  ]
}}
"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # レスポンスをパース
            response_text = message.content[0].text
            
            # JSONを抽出（```json ... ``` の中身を取得）
            if '```json' in response_text:
                json_start = response_text.index('```json') + 7
                json_end = response_text.index('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.index('```') + 3
                json_end = response_text.index('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text
            
            analysis = json.loads(json_text)
            
            logger.info("✅ AI analysis completed")
            return analysis
        
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            return self._fallback_analysis(audit_data)
    
    def _fallback_analysis(self, audit_data):
        """AIが使えない場合のフォールバック分析"""
        issues = audit_data.get('issues', [])
        
        # シンプルなルールベース分析
        risk_level = 'LOW'
        if any(i.get('severity') == 'CRITICAL' for i in issues):
            risk_level = 'CRITICAL'
        elif any(i.get('severity') == 'HIGH' for i in issues):
            risk_level = 'HIGH'
        elif any(i.get('severity') == 'MEDIUM' for i in issues):
            risk_level = 'MEDIUM'
        
        return {
            'risk_level': risk_level,
            'summary': f'{len(issues)}件の問題を検出しました。',
            'improvements': [
                {
                    'priority': 1,
                    'title': '検出された問題の確認',
                    'description': '監査ログを確認してください',
                    'implementation': 'cat /root/security_reports/security_audit_*.json | tail -1',
                    'estimated_impact': '問題の詳細把握'
                }
            ],
            'automated_fixes': []
        }
    
    def generate_report(self, audit_data, analysis):
        """レポートを生成"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'Mana Guard AI',
            'audit_data': audit_data,
            'ai_analysis': analysis,
            'recommendations': analysis.get('improvements', []),
            'automated_fixes': analysis.get('automated_fixes', [])
        }
        
        # レポートをファイルに保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.report_dir / f'mana_guard_report_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Report saved to {report_file}")
        return report_file
    
    def send_slack_notification(self, report_file):
        """Slackに通知を送信"""
        try:
            from security_vault_v2 import SecurityVaultV2
            vault = SecurityVaultV2()
            slack_webhook = vault.get('SLACK_WEBHOOK_URL')
            
            if not slack_webhook:
                logger.warning("⚠️ Slack webhook not configured")
                return False
            
            # レポートを読み込み
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            analysis = report.get('ai_analysis', {})
            risk_level = analysis.get('risk_level', 'UNKNOWN')
            summary = analysis.get('summary', 'セキュリティ監査完了')
            
            # Slack通知を送信
            import requests
            
            risk_emoji = {
                'LOW': '🟢',
                'MEDIUM': '🟡',
                'HIGH': '🟠',
                'CRITICAL': '🔴'
            }.get(risk_level, '⚪')
            
            message = {
                'text': f'{risk_emoji} *Mana Guard AI - セキュリティレポート*',
                'blocks': [
                    {
                        'type': 'header',
                        'text': {
                            'type': 'plain_text',
                            'text': f'{risk_emoji} Mana Guard AI セキュリティレポート'
                        }
                    },
                    {
                        'type': 'section',
                        'fields': [
                            {'type': 'mrkdwn', 'text': f'*リスクレベル:*\n{risk_level}'},
                            {'type': 'mrkdwn', 'text': f'*生成時刻:*\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'}
                        ]
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*要約:*\n{summary}'
                        }
                    }
                ]
            }
            
            # 改善提案を追加
            improvements = analysis.get('improvements', [])[:3]
            if improvements:
                message['blocks'].append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': '*🔧 改善提案:*\n' + '\n'.join([
                            f"{i+1}. {imp.get('title', 'N/A')}"
                            for i, imp in enumerate(improvements)
                        ])
                    }
                })
            
            response = requests.post(slack_webhook, json=message, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Slack notification sent")
                return True
            else:
                logger.warning(f"⚠️ Slack notification failed: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Slack notification error: {e}")
            return False
    
    def execute_automated_fixes(self, analysis, dry_run=True):
        """自動修復を実行"""
        automated_fixes = analysis.get('automated_fixes', [])
        
        if not automated_fixes:
            logger.info("✅ No automated fixes needed")
            return []
        
        results = []
        
        for fix in automated_fixes:
            if fix.get('requires_approval', True) and not dry_run:
                logger.info(f"⏭️ Skipping fix (requires approval): {fix.get('issue')}")
                results.append({
                    'fix': fix,
                    'status': 'skipped',
                    'reason': 'requires_approval'
                })
                continue
            
            if dry_run:
                logger.info(f"🔍 [DRY RUN] Would execute: {fix.get('fix_command')}")
                results.append({
                    'fix': fix,
                    'status': 'dry_run',
                    'command': fix.get('fix_command')
                })
            else:
                try:
                    logger.info(f"🔧 Executing fix: {fix.get('issue')}")
                    result = subprocess.run(
                        fix.get('fix_command'),
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    results.append({
                        'fix': fix,
                        'status': 'success' if result.returncode == 0 else 'failed',
                        'output': result.stdout,
                        'error': result.stderr
                    })
                    
                    if result.returncode == 0:
                        logger.info("✅ Fix applied successfully")
                    else:
                        logger.warning(f"⚠️ Fix failed: {result.stderr}")
                
                except Exception as e:
                    logger.error(f"❌ Fix execution error: {e}")
                    results.append({
                        'fix': fix,
                        'status': 'error',
                        'error': str(e)
                    })
        
        return results
    
    def run_full_cycle(self, dry_run=True, send_notification=True):
        """完全な監査サイクルを実行"""
        logger.info("🚀 Starting Mana Guard AI full cycle...")
        
        # 1. セキュリティ監査を実行
        audit_data = self.run_security_audit()
        
        # 2. AI分析
        analysis = self.analyze_audit_results(audit_data)
        
        # 3. レポート生成
        report_file = self.generate_report(audit_data, analysis)
        
        # 4. 自動修復（dry_runモード）
        fix_results = self.execute_automated_fixes(analysis, dry_run=dry_run)
        
        # 5. Slack通知
        if send_notification:
            self.send_slack_notification(report_file)
        
        # 結果サマリー
        summary = {
            'timestamp': datetime.now().isoformat(),
            'audit_status': audit_data.get('status', 'completed'),
            'risk_level': analysis.get('risk_level', 'UNKNOWN'),
            'improvements_count': len(analysis.get('improvements', [])),
            'fixes_applied': len([f for f in fix_results if f['status'] == 'success']),
            'report_file': str(report_file)
        }
        
        logger.info("✅ Mana Guard AI cycle completed")
        logger.info(f"📊 Summary: {json.dumps(summary, indent=2)}")
        
        return summary

# CLI
if __name__ == "__main__":
    import sys
    
    guard = ManaGuardAI()
    
    if len(sys.argv) < 2:
        print("Usage: mana_guard_ai.py [audit|analyze|report|full]")
        print("\nCommands:")
        print("  audit   - Run security audit only")
        print("  analyze - Run audit and AI analysis")
        print("  report  - Generate full report")
        print("  full    - Run complete cycle (audit + analyze + report + notify)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'audit':
        audit_data = guard.run_security_audit()
        print(json.dumps(audit_data, indent=2, ensure_ascii=False))
    
    elif command == 'analyze':
        audit_data = guard.run_security_audit()
        analysis = guard.analyze_audit_results(audit_data)
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    elif command == 'report':
        audit_data = guard.run_security_audit()
        analysis = guard.analyze_audit_results(audit_data)
        report_file = guard.generate_report(audit_data, analysis)
        print(f"✅ Report generated: {report_file}")
    
    elif command == 'full':
        dry_run = '--no-dry-run' not in sys.argv
        send_notification = '--no-notify' not in sys.argv
        
        summary = guard.run_full_cycle(dry_run=dry_run, send_notification=send_notification)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

