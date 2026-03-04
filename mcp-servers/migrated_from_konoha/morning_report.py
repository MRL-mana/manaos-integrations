#!/usr/bin/env python3
"""
毎朝の天気・予定配信システム
秋田市の天気予報とGoogle Calendarの予定をTelegram・Slackに配信
時間別天気通知機能付き
"""

import os
import json
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import re
import schedule
import time

class MorningReport:
    def __init__(self):
        self.akita_city = "秋田市"
        self.daisen_city = "大仙市"
        self.weather_api = "wttr.in"
        
        # 設定ファイル読み込み
        self.load_config()
    
    def load_config(self):
        """設定を読み込み"""
        # Slack設定
        slack_token_file = Path("/root/.mana_vault/slack_bot_token")
        if slack_token_file.exists():
            with open(slack_token_file, 'r') as f:
                self.slack_token = f.read().strip()
        
        # Telegram設定（既存のBotから取得）
        self.telegram_chat_id = self.get_telegram_chat_id()
    
    def get_telegram_chat_id(self):
        """Telegram Chat IDを取得"""
        # 既存の設定から取得を試行
        try:
            # 設定ファイルから読み込み
            config_file = Path("/root/projects/automation/telegram_config.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('chat_id')
        except:
            pass
        
        # デフォルト値（後で設定）
        return None
    
    def get_weather_forecast(self, city):
        """天気予報を取得"""
        try:
            # 詳細な天気予報を取得
            url = f"https://{self.weather_api}/{city}?lang=ja"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                weather_text = response.text
                
                # 今日の天気を抽出
                today_weather = self.parse_weather(weather_text)
                return today_weather
            else:
                return f"天気情報の取得に失敗しました ({response.status_code})"
                
        except Exception as e:
            return f"天気情報の取得エラー: {str(e)}"
    
    def parse_weather(self, weather_text):
        """天気テキストを解析"""
        lines = weather_text.split('\n')
        
        # 現在の天気を探す
        current_weather = "不明"
        current_temp = "不明"
        wind_speed = "不明"
        humidity = "不明"
        
        # 時間別天気予報
        weather_forecast = {
            "morning": "不明",
            "afternoon": "不明", 
            "evening": "不明",
            "night": "不明"
        }
        
        # より詳細な解析
        for i, line in enumerate(lines):
            # 温度を探す（°F表記）
            temp_match = re.search(r'(\+|-)?(\d+)°F', line)
            if temp_match and current_temp == "不明":
                temp_f = int(temp_match.group(2))
                if temp_match.group(1) == '-':
                    temp_f = -temp_f
                temp_c = round((temp_f - 32) * 5/9)
                current_temp = f"{temp_c}℃"
            
            # 湿度を探す
            humidity_match = re.search(r'(\d+)%', line)
            if humidity_match and humidity == "不明":
                humidity = f"{humidity_match.group(1)}%"
            
            # 風速を探す
            wind_match = re.search(r'(\d+)\s*(mph|km/h|m/s)', line)
            if wind_match and wind_speed == "不明":
                wind_speed = f"{wind_match.group(1)}{wind_match.group(2)}"
            
            # 天気を探す（絵文字と文字の組み合わせ）
            if "晴" in line and ("☀" in line or "🌞" in line):
                current_weather = "☀️ 晴れ"
            elif "曇" in line and ("☁" in line or "⛅" in line):
                current_weather = "☁️ 曇り"
            elif "雨" in line and ("🌧" in line or "💧" in line):
                current_weather = "🌧️ 雨"
            elif "雪" in line and ("❄" in line or "🌨" in line):
                current_weather = "❄️ 雪"
            elif "靄" in line or "霧" in line:
                current_weather = "🌫️ 靄"
            
            # 風速を探す（矢印とmphの組み合わせ）
            if "mph" in line and any(arrow in line for arrow in ["↑", "↓", "→", "←", "↗", "↘", "↙", "↖"]):
                wind_match = re.search(r'(\d+)-?(\d+)?\s*mph', line)
                if wind_match:
                    if wind_match.group(2):
                        wind_speed = f"{wind_match.group(1)}-{wind_match.group(2)} mph"
                    else:
                        wind_speed = f"{wind_match.group(1)} mph"
        
        # デフォルト値の設定
        if current_weather == "不明":
            current_weather = "🌤️ 天気不明"
        if current_temp == "不明":
            current_temp = "温度不明"
        if wind_speed == "不明":
            wind_speed = "風速不明"
        
        # 時間別天気予報の解析（簡易版）
        # 実際のAPIでは詳細な時間別データが取得できる場合が多い
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            weather_forecast["morning"] = current_weather
        elif 12 <= current_hour < 17:
            weather_forecast["afternoon"] = current_weather
        elif 17 <= current_hour < 21:
            weather_forecast["evening"] = current_weather
        else:
            weather_forecast["night"] = current_weather
        
        # デフォルト値の設定
        if current_weather == "不明":
            current_weather = "🌤️ 天気不明"
        if current_temp == "不明":
            current_temp = "温度不明"
        if wind_speed == "不明":
            wind_speed = "風速不明"
        if humidity == "不明":
            humidity = "湿度不明"
        
        return {
            "weather": current_weather,
            "temperature": current_temp,
            "wind": wind_speed,
            "humidity": humidity,
            "forecast": weather_forecast
        }
    
    def get_calendar_events(self):
        """Google Calendarの予定を取得"""
        try:
            # Trinity Google Servicesを使用
            calendar_script = Path("/root/trinity_workspace/tools/google_calendar.py")
            if calendar_script.exists():
                result = subprocess.run([
                    "python3", str(calendar_script), "--today"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return f"予定取得エラー: {result.stderr}"
            else:
                return "Google Calendar連携が設定されていません"
                
        except Exception as e:
            return f"予定取得エラー: {str(e)}"
    
    def get_todo_list(self):
        """やることリストを取得"""
        try:
            # Trinity Workspaceのタスクファイルを確認
            tasks_file = Path("/root/trinity_workspace/shared/tasks.json")
            if tasks_file.exists():
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                
                # 今日のタスクを抽出
                today = datetime.now().strftime("%Y-%m-%d")
                today_tasks = []
                
                for task in tasks_data.get('tasks', []):
                    if task.get('date') == today or task.get('status') == 'pending':
                        today_tasks.append(f"• {task.get('content', 'タスク不明')}")
                
                if today_tasks:
                    return "\n".join(today_tasks[:5])  # 最大5件
                else:
                    return "今日のタスクはありません"
            else:
                return "タスクファイルが見つかりません"
                
        except Exception as e:
            return f"タスク取得エラー: {str(e)}"
    
    def format_report(self):
        """レポートをフォーマット"""
        today = datetime.now().strftime("%Y年%m月%d日 (%A)")
        
        # 天気情報取得
        akita_weather = self.get_weather_forecast(self.akita_city)
        daisen_weather = self.get_weather_forecast(self.daisen_city)
        
        # 型チェック：文字列の場合は辞書に変換
        if isinstance(akita_weather, str):
            akita_weather = {'weather': akita_weather, 'temperature': '不明', 'wind': '不明', 'humidity': '不明', 'forecast': {'morning': '不明', 'afternoon': '不明', 'evening': '不明', 'night': '不明'}}
        if isinstance(daisen_weather, str):
            daisen_weather = {'weather': daisen_weather, 'temperature': '不明', 'wind': '不明', 'humidity': '不明', 'forecast': {'morning': '不明', 'afternoon': '不明', 'evening': '不明', 'night': '不明'}}
        
        # 予定取得
        calendar_events = self.get_calendar_events()
        
        # やることリスト取得
        todo_list = self.get_todo_list()
        
        # レポート作成
        report = f"""🌅 **{today} 朝のレポート** 🌅

🏠 **秋田市（自宅）**
天気: {akita_weather.get('weather', '不明')}
気温: {akita_weather.get('temperature', '不明')}
風速: {akita_weather.get('wind', '不明')}
湿度: {akita_weather.get('humidity', '不明')}

💼 **大仙市（職場）**
天気: {daisen_weather.get('weather', '不明')}
気温: {daisen_weather.get('temperature', '不明')}
風速: {daisen_weather.get('wind', '不明')}
湿度: {daisen_weather.get('humidity', '不明')}

🌤️ **今日の天気予報**
🌅 午前: {akita_weather.get('forecast', {}).get('morning', '不明')}
☀️ 午後: {akita_weather.get('forecast', {}).get('afternoon', '不明')}
🌆 夕方: {akita_weather.get('forecast', {}).get('evening', '不明')}
🌙 夜: {akita_weather.get('forecast', {}).get('night', '不明')}

📅 **今日の予定**
{calendar_events}

✅ **今日のやること**
{todo_list}

---
🤖 Trinity System より自動配信
"""
        
        return report
    
    def send_to_telegram(self, message):
        """Telegramに送信"""
        if not self.telegram_chat_id:
            print("Telegram Chat IDが設定されていません")
            return False
        
        try:
            # 既存のTelegram Botを使用
            bot_script = Path("/root/projects/automation/manaspec_telegram_bot.py")
            if bot_script.exists():
                # 直接Botスクリプトを呼び出し
                result = subprocess.run([
                    "python3", str(bot_script), "--send", message
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✅ Telegram送信成功")
                    return True
                else:
                    print(f"❌ Telegram送信失敗: {result.stderr}")
                    return False
            else:
                print("Telegram Botスクリプトが見つかりません")
                return False
                
        except Exception as e:
            print(f"Telegram送信エラー: {str(e)}")
            return False
    
    def send_to_slack(self, message):
        """Slackに送信"""
        if not hasattr(self, 'slack_token'):
            print("Slack Tokenが設定されていません")
            return False
        
        try:
            # Slack Web APIを使用
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self.slack_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "channel": "#general",  # チャンネル名を調整
                "text": message
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print("✅ Slack送信成功")
                    return True
                else:
                    print(f"❌ Slack送信失敗: {result.get('error')}")
                    return False
            else:
                print(f"❌ Slack送信失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Slack送信エラー: {str(e)}")
            return False
    
    def send_report(self):
        """レポートを送信"""
        print("🌅 朝のレポートを作成中...")
        
        # レポート作成
        report = self.format_report()
        print("\n" + "="*50)
        print(report)
        print("="*50)
        
        # 送信
        telegram_success = self.send_to_telegram(report)
        slack_success = self.send_to_slack(report)
        
        # 結果表示
        print(f"\n📊 送信結果:")
        print(f"  Telegram: {'✅' if telegram_success else '❌'}")
        print(f"  Slack: {'✅' if slack_success else '❌'}")
        
        return telegram_success or slack_success
    
    def send_weather_update(self, time_period):
        """時間別天気通知を送信"""
        try:
            # 天気情報取得
            akita_weather = self.get_weather_forecast(self.akita_city)
            daisen_weather = self.get_weather_forecast(self.daisen_city)
            
            # 型チェック
            if isinstance(akita_weather, str):
                akita_weather = {'weather': akita_weather, 'temperature': '不明', 'wind': '不明', 'humidity': '不明', 'forecast': {'morning': '不明', 'afternoon': '不明', 'evening': '不明', 'night': '不明'}}
            if isinstance(daisen_weather, str):
                daisen_weather = {'weather': daisen_weather, 'temperature': '不明', 'wind': '不明', 'humidity': '不明', 'forecast': {'morning': '不明', 'afternoon': '不明', 'evening': '不明', 'night': '不明'}}
            
            # 時間別メッセージ
            time_emoji = {
                "morning": "🌅",
                "afternoon": "☀️", 
                "evening": "🌆",
                "night": "🌙"
            }
            
            time_name = {
                "morning": "午前",
                "afternoon": "午後",
                "evening": "夕方", 
                "night": "夜"
            }
            
            emoji = time_emoji.get(time_period, "🌤️")
            name = time_name.get(time_period, time_period)
            
            # メッセージ作成
            message = f"""{emoji} **{name}の天気予報** {emoji}

🏠 **秋田市（自宅）**
天気: {akita_weather.get('weather', '不明')}
気温: {akita_weather.get('temperature', '不明')}
風速: {akita_weather.get('wind', '不明')}
湿度: {akita_weather.get('humidity', '不明')}

💼 **大仙市（職場）**
天気: {daisen_weather.get('weather', '不明')}
気温: {daisen_weather.get('temperature', '不明')}
風速: {daisen_weather.get('wind', '不明')}
湿度: {daisen_weather.get('humidity', '不明')}

---
🤖 Trinity System より自動配信"""
            
            # 送信
            telegram_success = self.send_to_telegram(message)
            slack_success = self.send_to_slack(message)
            
            print(f"\n📊 {name}天気通知送信結果:")
            print(f"  Telegram: {'✅' if telegram_success else '❌'}")
            print(f"  Slack: {'✅' if slack_success else '❌'}")
            
            return telegram_success or slack_success
            
        except Exception as e:
            print(f"❌ {name}天気通知エラー: {str(e)}")
            return False


def main():
    """メイン関数"""
    print("🌅 毎朝レポートシステム起動")
    
    reporter = MorningReport()
    success = reporter.send_report()
    
    if success:
        print("✅ レポート送信完了")
    else:
        print("❌ レポート送信失敗")


def schedule_weather_updates():
    """時間別天気通知のスケジュール設定"""
    reporter = MorningReport()
    
    # スケジュール設定
    schedule.every().day.at("09:00").do(lambda: reporter.send_weather_update("morning"))
    schedule.every().day.at("13:00").do(lambda: reporter.send_weather_update("afternoon"))
    schedule.every().day.at("17:00").do(lambda: reporter.send_weather_update("evening"))
    schedule.every().day.at("21:00").do(lambda: reporter.send_weather_update("night"))
    
    print("⏰ 時間別天気通知スケジュール設定完了")
    print("  🌅 午前: 09:00")
    print("  ☀️ 午後: 13:00")
    print("  🌆 夕方: 17:00")
    print("  🌙 夜: 21:00")
    
    # スケジュール実行
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        schedule_weather_updates()
    else:
        main()
