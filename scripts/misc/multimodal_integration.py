"""
マルチモーダル統合
画像・音声・テキストの統合処理
"""

import json
import base64
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import speech_recognition as sr
    import pyttsx3
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("音声処理ライブラリがインストールされていません。")
    print("インストール: pip install SpeechRecognition pyttsx3")

from langchain_integration import LangChainIntegration
from comfyui_integration import ComfyUIIntegration
from obsidian_integration import ObsidianIntegration


class MultimodalIntegration:
    """マルチモーダル統合クラス"""
    
    def __init__(self):
        """初期化"""
        self.langchain = LangChainIntegration()
        self.comfyui = ComfyUIIntegration()
        try:
            from pathlib import Path
            default_vault = Path.home() / "Documents" / "Obsidian"
            if default_vault.exists():
                self.obsidian = ObsidianIntegration(str(default_vault))
            else:
                self.obsidian = ObsidianIntegration(str(Path.cwd()))
        except Exception:
            self.obsidian = None
        
        self.speech_recognizer = None
        self.speech_engine = None
        
        if SPEECH_AVAILABLE:
            self._initialize_speech()
    
    def _initialize_speech(self):
        """音声処理を初期化"""
        try:
            self.speech_recognizer = sr.Recognizer()
            self.speech_engine = pyttsx3.init()
        except Exception as e:
            print(f"音声処理初期化エラー: {e}")
    
    def text_to_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512
    ) -> Dict[str, Any]:
        """
        テキストから画像を生成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            
        Returns:
            実行結果
        """
        result = {
            "type": "text_to_image",
            "prompt": prompt,
            "success": False
        }
        
        if self.comfyui.is_available():
            prompt_id = self.comfyui.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height
            )
            
            if prompt_id:
                result["success"] = True
                result["prompt_id"] = prompt_id
        else:
            result["error"] = "ComfyUIが利用できません"
        
        return result
    
    def image_to_text(
        self,
        image_path: str,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        画像からテキストを生成（説明・質問応答）
        
        Args:
            image_path: 画像パス
            question: 質問（オプション）
            
        Returns:
            実行結果
        """
        result = {
            "type": "image_to_text",
            "image_path": image_path,
            "success": False
        }
        
        if not self.langchain.is_available():
            result["error"] = "LangChainが利用できません"
            return result
        
        # 画像を読み込み（base64エンコード）
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            result["error"] = f"画像読み込みエラー: {e}"
            return result
        
        # LangChainで画像を分析
        if question:
            prompt = f"この画像について、以下の質問に答えてください: {question}\n\n画像データ: {image_data[:100]}..."
        else:
            prompt = f"この画像を詳しく説明してください。\n\n画像データ: {image_data[:100]}..."
        
        response = self.langchain.chat(prompt)
        
        result["success"] = True
        result["description"] = response
        
        return result
    
    def text_to_speech(self, text: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        テキストを音声に変換
        
        Args:
            text: テキスト
            save_path: 保存パス（オプション）
            
        Returns:
            実行結果
        """
        result = {
            "type": "text_to_speech",
            "text": text,
            "success": False
        }
        
        if not SPEECH_AVAILABLE or not self.speech_engine:
            result["error"] = "音声処理が利用できません"
            return result
        
        try:
            if save_path:
                self.speech_engine.save_to_file(text, save_path)
                self.speech_engine.runAndWait()
                result["success"] = True
                result["audio_path"] = save_path
            else:
                self.speech_engine.say(text)
                self.speech_engine.runAndWait()
                result["success"] = True
        except Exception as e:
            result["error"] = f"音声変換エラー: {e}"
        
        return result
    
    def speech_to_text(self, audio_path: str) -> Dict[str, Any]:
        """
        音声をテキストに変換
        
        Args:
            audio_path: 音声ファイルパス
            
        Returns:
            実行結果
        """
        result = {
            "type": "speech_to_text",
            "audio_path": audio_path,
            "success": False
        }
        
        if not SPEECH_AVAILABLE or not self.speech_recognizer:
            result["error"] = "音声処理が利用できません"
            return result
        
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self.speech_recognizer.record(source)
                text = self.speech_recognizer.recognize_google(audio, language='ja-JP')
                
                result["success"] = True
                result["text"] = text
        except sr.UnknownValueError:
            result["error"] = "音声を認識できませんでした"
        except sr.RequestError as e:
            result["error"] = f"音声認識サービスエラー: {e}"
        except Exception as e:
            result["error"] = f"音声変換エラー: {e}"
        
        return result
    
    def multimodal_workflow(
        self,
        input_type: str,
        input_data: str,
        output_type: str
    ) -> Dict[str, Any]:
        """
        マルチモーダルワークフロー
        
        Args:
            input_type: 入力タイプ（text, image, speech）
            input_data: 入力データ（テキスト、画像パス、音声パス）
            output_type: 出力タイプ（text, image, speech）
            
        Returns:
            実行結果
        """
        result = {
            "input_type": input_type,
            "output_type": output_type,
            "success": False
        }
        
        # 入力処理
        if input_type == "speech":
            speech_result = self.speech_to_text(input_data)
            if not speech_result["success"]:
                result["error"] = speech_result.get("error", "音声変換に失敗")
                return result
            text = speech_result["text"]
        elif input_type == "image":
            image_result = self.image_to_text(input_data)
            if not image_result["success"]:
                result["error"] = image_result.get("error", "画像解析に失敗")
                return result
            text = image_result["description"]
        else:
            text = input_data
        
        # 出力処理
        if output_type == "image":
            image_result = self.text_to_image(text)
            result.update(image_result)
        elif output_type == "speech":
            speech_result = self.text_to_speech(text)
            result.update(speech_result)
        else:
            # テキスト出力（LangChainで処理）
            if self.langchain.is_available():
                response = self.langchain.chat(f"以下の内容を処理してください: {text}")
                result["success"] = True
                result["text"] = response
            else:
                result["success"] = True
                result["text"] = text
        
        return result
    
    def create_multimodal_note(
        self,
        title: str,
        text_content: str,
        image_paths: Optional[List[str]] = None,
        audio_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        マルチモーダルノートを作成
        
        Args:
            title: タイトル
            text_content: テキスト内容
            image_paths: 画像パスのリスト
            audio_path: 音声ファイルパス
            
        Returns:
            実行結果
        """
        result = {
            "type": "multimodal_note",
            "success": False
        }
        
        # ノート内容を構築
        content = text_content
        
        if image_paths:
            content += "\n\n## 画像\n\n"
            for img_path in image_paths:
                content += f"![画像]({img_path})\n\n"
        
        if audio_path:
            content += f"\n\n## 音声\n\n[音声ファイル]({audio_path})\n\n"
        
        # Obsidianにノート作成
        if self.obsidian and self.obsidian.is_available():
            note_path = self.obsidian.create_note(
                title=title,
                content=content,
                tags=["マルチモーダル", "ManaOS"]
            )
            
            if note_path:
                result["success"] = True
                result["note_path"] = str(note_path)
            else:
                result["error"] = "ノート作成に失敗"
        else:
            result["error"] = "Obsidianが利用できません"
        
        return result


def main():
    """テスト用メイン関数"""
    print("マルチモーダル統合テスト")
    print("=" * 60)
    
    multimodal = MultimodalIntegration()
    
    # テキストから画像生成
    print("\nテキストから画像生成:")
    result = multimodal.text_to_image("a beautiful landscape")
    print(f"結果: {result}")
    
    # マルチモーダルワークフロー
    print("\nマルチモーダルワークフロー:")
    result = multimodal.multimodal_workflow(
        input_type="text",
        input_data="a cat sitting on a windowsill",
        output_type="image"
    )
    print(f"結果: {result}")


if __name__ == "__main__":
    main()



