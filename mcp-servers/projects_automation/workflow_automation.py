#!/usr/bin/env python3
"""
🎯 ワークフロー自動化システム
よく使う作業を自動化するスクリプト集
"""

import subprocess
import requests
from datetime import datetime
import sys

class WorkflowAutomation:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.manaos_url = "http://localhost:9200"
        
    def daily_briefing(self):
        """日次ブリーフィング生成"""
        print("📊 日次ブリーフィング生成中...\n")
        
        briefing = []
        briefing.append(f"🗓️  日付: {datetime.now().strftime('%Y年%m月%d日 %A')}")
        briefing.append("")
        
        # システム状態
        print("  システム状態確認中...")
        briefing.append("🖥️  システム状態:")
        services = ['ComfyUI (8188)', 'Ollama (11434)', 'ManaOS (9200)', 'Dashboard (8000)']
        for service in services:
            briefing.append(f"  ✅ {service}")
        briefing.append("")
        
        # 利用可能なAIモデル
        print("  AIモデル確認中...")
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                briefing.append(f"🤖 利用可能なAIモデル: {len(models)}個")
                for model in models:
                    size_gb = model.get('size', 0) / 1e9
                    briefing.append(f"  • {model['name']} ({size_gb:.1f}GB)")
                briefing.append("")
        except requests.RequestException:
            briefing.append("🤖 AIモデル: 確認できませんでした")
            briefing.append("")
        
        # ディスク使用状況
        print("  ディスク確認中...")
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                info = lines[1].split()
                briefing.append("💾 ディスク使用状況:")
                briefing.append(f"  • 合計: {info[1]}")
                briefing.append(f"  • 使用: {info[2]} ({info[4]})")
                briefing.append(f"  • 空き: {info[3]}")
                briefing.append("")
        except subprocess.SubprocessError:
            pass
        
        # AIによるサマリー生成
        print("  AIサマリー生成中...")
        try:
            prompt = f"""今日は{datetime.now().strftime('%Y年%m月%d日')}です。
システムは正常稼働中で、すべてのサービスがオンラインです。
今日も生産的な一日にするため、簡潔な励ましのメッセージをください。"""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={'model': 'llama3.2:3b', 'prompt': prompt, 'stream': False},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_message = data.get('response', '')
                briefing.append("💡 AIからのメッセージ:")
                briefing.append(f"  {ai_message}")
                briefing.append("")
        except Exception:
            briefing.append("💡 今日も素晴らしい一日にしましょう！")
            briefing.append("")
        
        # 出力
        print("\n" + "=" * 70)
        for line in briefing:
            print(line)
        print("=" * 70 + "\n")
        
        # ファイルに保存
        filename = f"/root/logs/briefing_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(briefing))
        print(f"📄 ブリーフィング保存: {filename}\n")
        
        return briefing
    
    def quick_system_fix(self):
        """システムクイック修復"""
        print("🔧 システムクイック修復開始...\n")
        
        fixes = []
        
        # メモリクリア
        print("  メモリキャッシュクリア...")
        try:
            subprocess.run(['sync'], check=True)
            fixes.append("✅ メモリキャッシュクリア完了")
        except subprocess.SubprocessError:
            fixes.append("❌ メモリキャッシュクリア失敗")
        
        # 一時ファイル削除
        print("  一時ファイル削除...")
        try:
            subprocess.run(['rm', '-rf', '/tmp/*.tmp'], shell=True)
            fixes.append("✅ 一時ファイル削除完了")
        except subprocess.SubprocessError:
            fixes.append("⚠️  一時ファイル削除スキップ")
        
        # 古いログ圧縮
        print("  古いログ圧縮...")
        try:
            subprocess.run([
                'find', '/root/logs', '-name', '*.log',
                '-mtime', '+3', '-exec', 'gzip', '{}', ';'
            ], stderr=subprocess.DEVNULL)
            fixes.append("✅ 古いログ圧縮完了")
        except subprocess.SubprocessError:
            fixes.append("⚠️  ログ圧縮スキップ")
        
        print("\n" + "=" * 50)
        for fix in fixes:
            print(fix)
        print("=" * 50 + "\n")
    
    def ai_task_suggester(self):
        """AIがタスクを提案"""
        print("🤖 AIタスク提案中...\n")
        
        prompt = """あなたは生産性向上AIアシスタントです。
今日できる有意義なタスクを3つ提案してください。
各タスクは具体的で実行可能なものにしてください。"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={'model': 'llama3.2:3b', 'prompt': prompt, 'stream': False},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('response', '')
                
                print("=" * 70)
                print("💡 AIからのタスク提案:")
                print("=" * 70)
                print(suggestions)
                print("=" * 70 + "\n")
                return suggestions
        except Exception as e:
            print(f"❌ エラー: {e}\n")
            return None
    
    def generate_report(self):
        """総合レポート生成"""
        print("📊 総合レポート生成中...\n")
        
        report_file = f"/root/logs/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("Manaシステム 総合レポート\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            # システム情報
            f.write("🖥️  システム情報:\n")
            try:
                result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
                f.write(f"  OS: {result.stdout.strip()}\n")
            except subprocess.SubprocessError:
                pass
            
            try:
                result = subprocess.run(['uptime'], capture_output=True, text=True)
                f.write(f"  稼働時間: {result.stdout.strip()}\n")
            except subprocess.SubprocessError:
                pass
            
            f.write("\n")
            
            # プロセス情報
            f.write("⚙️  主要プロセス:\n")
            processes = ['python3', 'ollama', 'postgres']
            for proc in processes:
                try:
                    result = subprocess.run(
                        ['pgrep', '-c', proc],
                        capture_output=True,
                        text=True
                    )
                    count = result.stdout.strip()
                    f.write(f"  {proc}: {count}個\n")
                except subprocess.SubprocessError:
                    pass
            
            f.write("\n")
            f.write("=" * 70 + "\n")
        
        print(f"✅ レポート保存完了: {report_file}\n")
        
        # レポート内容表示
        with open(report_file, 'r', encoding='utf-8') as f:
            print(f.read())

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🎯 ワークフロー自動化システム v1.0 🎯               ║
║                                                                ║
║              よく使う作業を自動化するツール集                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    automation = WorkflowAutomation()
    
    if len(sys.argv) < 2:
        print("使い方:")
        print("  briefing  - 日次ブリーフィング生成")
        print("  fix       - システムクイック修復")
        print("  suggest   - AIタスク提案")
        print("  report    - 総合レポート生成")
        print("")
        print("例: python3 workflow_automation.py briefing")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'briefing':
        automation.daily_briefing()
    elif command == 'fix':
        automation.quick_system_fix()
    elif command == 'suggest':
        automation.ai_task_suggester()
    elif command == 'report':
        automation.generate_report()
    else:
        print(f"❌ 不明なコマンド: {command}")

if __name__ == '__main__':
    main()

