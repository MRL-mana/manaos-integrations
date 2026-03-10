#!/usr/bin/env python3
"""
音声メモ機能
音声録音、Whisper文字起こし、ノートブックに自動追加
"""

import whisper
import torch
from datetime import datetime
from pathlib import Path
from typing import Dict


class VoiceMemo:
    """音声メモ機能"""
    
    def __init__(self):
        self.temp_dir = Path("/tmp/voice_memos")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Whisperモデルロード
        print("🎤 Whisperモデルロード中...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_model = whisper.load_model("base", device=device)
        print(f"✅ Whisperモデルロード完了（デバイス: {device}）")
    
    def transcribe_audio(self, audio_path: str, language: str = 'ja') -> Dict:
        """音声文字起こし"""
        try:
            print(f"🎤 音声文字起こし中: {audio_path}")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                task='transcribe'
            )
            
            text = result["text"].strip()
            segments = result.get("segments", [])
            
            print(f"✅ 文字起こし完了: {len(text)}文字")
            
            return {
                "success": True,
                "text": text,
                "language": result.get("language", language),
                "segments": [
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "")
                    }
                    for seg in segments
                ],
                "word_count": len(text.split())
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_memo(self, audio_path: str, notebook_id: str = None, language: str = 'ja') -> Dict:  # type: ignore
        """音声メモ作成"""
        try:
            # 文字起こし
            transcript = self.transcribe_audio(audio_path, language)
            
            if not transcript["success"]:
                return {"success": False, "error": "文字起こし失敗"}
            
            # メモデータ作成
            memo = {
                "type": "voice_memo",
                "text": transcript["text"],
                "language": transcript["language"],
                "word_count": transcript["word_count"],
                "segments": transcript["segments"],
                "created_at": datetime.now().isoformat(),
                "audio_path": audio_path,
                "notebook_id": notebook_id
            }
            
            return {
                "success": True,
                "memo": memo
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def batch_transcribe(self, audio_files: list, language: str = 'ja') -> Dict:
        """複数音声ファイル一括文字起こし"""
        try:
            results = []
            
            for i, audio_path in enumerate(audio_files, 1):
                print(f"🎤 [{i}/{len(audio_files)}] 処理中: {audio_path}")
                
                result = self.transcribe_audio(audio_path, language)
                
                if result["success"]:
                    results.append({
                        "audio_path": audio_path,
                        "text": result["text"],
                        "word_count": result["word_count"]
                    })
            
            return {
                "success": True,
                "results": results,
                "total": len(results)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}

