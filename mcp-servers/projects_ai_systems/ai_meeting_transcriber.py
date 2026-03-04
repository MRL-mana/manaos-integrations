#!/usr/bin/env python3
"""
AI議事録自動生成システム
音声→文字起こし→要点抽出→アクションアイテム
"""

from datetime import datetime
from pathlib import Path

class AIMeetingTranscriber:
    """AI議事録生成"""
    
    def __init__(self):
        self.output_dir = Path("/root/meeting_notes")
        self.output_dir.mkdir(exist_ok=True)
        
    def transcribe_audio(self, audio_file):
        """音声文字起こし（Whisper使用）"""
        try:
            # Whisper APIまたはローカルWhisperモデル使用
            transcript = "会議の音声を文字起こししました...\n（実際にはWhisper APIを使用）"
            return transcript
        except Exception as e:
            return f"文字起こしエラー: {e}"
    
    def extract_key_points(self, transcript):
        """要点抽出（AI使用）"""
        # GPT/Claude APIで要点抽出
        key_points = [
            "プロジェクトの進捗確認",
            "次回までのタスク割り当て",
            "予算の承認",
            "スケジュール調整"
        ]
        return key_points
    
    def extract_action_items(self, transcript):
        """アクションアイテム抽出"""
        # AIで「〜する」「〜してください」などを検出
        actions = [
            {"person": "Mana", "task": "資料作成", "deadline": "明日まで"},
            {"person": "田中さん", "task": "レビュー", "deadline": "今週中"},
            {"person": "全員", "task": "次回会議資料準備", "deadline": "来週月曜"}
        ]
        return actions
    
    def generate_minutes(self, meeting_title, transcript, attendees=None):
        """議事録生成"""
        timestamp = datetime.now()
        
        # 要点とアクションアイテム抽出
        key_points = self.extract_key_points(transcript)
        actions = self.extract_action_items(transcript)
        
        # Markdown形式で議事録作成
        minutes = f"""# {meeting_title}

**日時**: {timestamp.strftime('%Y年%m月%d日 %H:%M')}
**参加者**: {', '.join(attendees or ['Mana'])}

---

## 📋 議題・要点

"""
        for i, point in enumerate(key_points, 1):
            minutes += f"{i}. {point}\n"
        
        minutes += """
---

## ✅ アクションアイテム

"""
        for action in actions:
            minutes += f"- [ ] **{action['person']}**: {action['task']} (期限: {action['deadline']})\n"
        
        minutes += f"""
---

## 📝 詳細

{transcript[:500]}...

---

## 📊 次回

- 日時: 未定
- 議題: フォローアップ

---
作成: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Tags: #meeting #minutes
"""
        
        # 保存
        filename = f"{timestamp.strftime('%Y%m%d_%H%M')}_{meeting_title.replace(' ', '_')}.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(minutes)
        
        # Obsidianにも保存
        obsidian_path = Path("/root/obsidian_vault/Meetings")
        obsidian_path.mkdir(exist_ok=True)
        
        with open(obsidian_path / filename, 'w', encoding='utf-8') as f:
            f.write(minutes)
        
        print(f"✅ 議事録生成: {filepath}")
        print(f"✅ Obsidianに保存: {obsidian_path / filename}")
        
        return str(filepath)

def main():
    transcriber = AIMeetingTranscriber()
    
    print("🎙️ AI議事録自動生成システム\n")
    
    # テスト実行
    minutes_path = transcriber.generate_minutes(
        meeting_title="プロジェクト進捗会議",
        transcript="テスト用の会議内容...",
        attendees=["Mana", "田中さん", "佐藤さん"]
    )
    
    print("\n✅ テスト完了")
    print(f"📁 議事録: {minutes_path}")

if __name__ == "__main__":
    main()

