#!/usr/bin/env python3
"""
YouTube動画処理モジュール
動画ダウンロード、音声抽出、文字起こし
"""

import yt_dlp
import whisper
import os
from pathlib import Path
from typing import Dict, Optional
import torch


class YouTubeHandler:
    """YouTube動画処理"""
    
    def __init__(self):
        self.temp_dir = Path("/tmp/youtube_downloads")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Whisperモデルロード
        print("🎤 Whisperモデルロード中...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_model = whisper.load_model("base", device=device)
        print(f"✅ Whisperモデルロード完了（デバイス: {device}）")
    
    def process(self, url: str) -> Dict:
        """YouTube動画を処理"""
        try:
            # 動画情報取得
            video_info = self._get_video_info(url)
            if not video_info["success"]:
                return video_info
            
            # 音声ダウンロード
            audio_path = self._download_audio(url)
            if not audio_path:
                return {"success": False, "error": "音声ダウンロード失敗"}
            
            # 文字起こし
            transcript = self._transcribe_audio(audio_path)
            
            # クリーンアップ
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "success": True,
                "video_info": video_info,
                "transcript": transcript
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_video_info(self, url: str) -> Dict:
        """動画情報取得"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "success": True,
                    "title": info.get('title', ''),
                    "description": info.get('description', ''),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', ''),
                    "upload_date": info.get('upload_date', ''),
                    "view_count": info.get('view_count', 0),
                    "thumbnail": info.get('thumbnail', '')
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _download_audio(self, url: str) -> Optional[str]:
        """音声ダウンロード"""
        try:
            output_path = self.temp_dir / "audio_%(id)s.%(ext)s"
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path),
                'quiet': True,
                'no_warnings': True,
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192K',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # mp3に変換
                if not filename.endswith('.mp3'):
                    mp3_path = filename.rsplit('.', 1)[0] + '.mp3'
                    if os.path.exists(mp3_path):
                        return mp3_path
                
                return filename
        
        except Exception as e:
            print(f"音声ダウンロードエラー: {e}")
            return None
    
    def _transcribe_audio(self, audio_path: str) -> Dict:
        """音声文字起こし"""
        try:
            print(f"🎤 文字起こし開始: {audio_path}")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language='ja',
                task='transcribe'
            )
            
            text = result["text"].strip()
            segments = result.get("segments", [])
            
            print(f"✅ 文字起こし完了: {len(text)}文字")
            
            return {
                "text": text,
                "language": result.get("language", "ja"),
                "segments": [
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "")
                    }
                    for seg in segments
                ]
            }
        
        except Exception as e:
            return {"error": str(e)}


