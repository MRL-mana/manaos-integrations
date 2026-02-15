"""
NectarSTT統合
音声認識エンジンのManaOS統合
"""

import os
from manaos_logger import get_logger
from typing import Optional, Dict, Any
from pathlib import Path

logger = get_service_logger("nectarstt-integration")


class NectarSTTIntegration:
    """NectarSTT音声認識統合"""
    
    def __init__(self, enabled: bool = True):
        """
        初期化
        
        Args:
            enabled: 統合を有効にするか（デフォルト: True）
        """
        self.enabled = enabled
        self.nectarstt_path = Path("repos/NectarSTT")
        self.available = False
        
        if enabled:
            self._check_availability()
    
    def _check_availability(self) -> bool:
        """NectarSTTが利用可能か確認"""
        try:
            # Main-Engineの存在確認
            main_engine_path = self.nectarstt_path / "Main-Engine"
            if not main_engine_path.exists():
                logger.warning(f"NectarSTT Main-Engineが見つかりません: {main_engine_path}")
                logger.info("Main-Engine.zipをダウンロードして展開してください")
                return False
            
            # パッケージがインストールされているか確認
            try:
                import nectarstt
                self.available = True
                logger.info("NectarSTTが利用可能です")
                return True
            except ImportError:
                logger.warning("nectarsttパッケージがインストールされていません")
                logger.info("インストール: pip install nectarstt")
                return False
                
        except Exception as e:
            logger.error(f"NectarSTT確認エラー: {e}")
            return False
    
    def is_available(self) -> bool:
        """利用可能か確認"""
        return self.available and self.enabled
    
    def record_until_silence(self, silence_threshold: float = 0.01, timeout: float = 10.0) -> Optional[str]:
        """
        無音まで録音してテキストに変換
        
        Args:
            silence_threshold: 無音判定の閾値
            timeout: タイムアウト（秒）
            
        Returns:
            認識されたテキスト、エラーの場合はNone
        """
        if not self.is_available():
            logger.error("NectarSTTが利用できません")
            return None
        
        try:
            from nectarstt import record_until_silence
            
            logger.info("音声認識を開始します...")
            text = record_until_silence(
                silence_threshold=silence_threshold,
                timeout=timeout
            )
            
            if text:
                logger.info(f"認識結果: {text}")
            else:
                logger.warning("音声が認識されませんでした")
            
            return text
            
        except Exception as e:
            logger.error(f"音声認識エラー: {e}")
            return None
    
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        音声ファイルをテキストに変換
        
        Args:
            audio_file_path: 音声ファイルのパス
            
        Returns:
            認識されたテキスト、エラーの場合はNone
        """
        if not self.is_available():
            logger.error("NectarSTTが利用できません")
            return None
        
        try:
            # NectarSTTのファイル転写機能を使用
            # （実装はNectarSTTのAPIに依存）
            logger.info(f"ファイルを転写中: {audio_file_path}")
            
            # ここに実際の転写処理を実装
            # NectarSTTのAPIドキュメントに従って実装
            
            return None
            
        except Exception as e:
            logger.error(f"ファイル転写エラー: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス情報を取得"""
        return {
            "enabled": self.enabled,
            "available": self.is_available(),
            "path": str(self.nectarstt_path),
            "main_engine_exists": (self.nectarstt_path / "Main-Engine").exists() if self.nectarstt_path.exists() else False
        }


# 使用例
if __name__ == "__main__":
    # 統合をテスト
    integration = NectarSTTIntegration()
    
    print("ステータス:", integration.get_status())
    
    if integration.is_available():
        print("音声認識テスト...")
        text = integration.record_until_silence()
        print(f"認識結果: {text}")
    else:
        print("NectarSTTが利用できません。セットアップを確認してください。")


















