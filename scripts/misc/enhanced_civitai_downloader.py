"""
拡張CivitAIダウンローダー
既存のdownload_civitai_models.pyと統合システムを統合
"""

import sys
from pathlib import Path

# 既存のダウンローダーをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from download_civitai_models import CivitaiModelDownloader

from civitai_integration import CivitAIIntegration
from google_drive_integration import GoogleDriveIntegration
from obsidian_integration import ObsidianIntegration
from mem0_integration import Mem0Integration


class EnhancedCivitaiDownloader:
    """拡張CivitAIダウンローダー"""
    
    def __init__(self, output_dir: str = "models"):
        """
        初期化
        
        Args:
            output_dir: モデル保存ディレクトリ
        """
        self.downloader = CivitaiModelDownloader(output_dir)
        self.civitai = CivitAIIntegration()
        self.drive = GoogleDriveIntegration()
        self.obsidian = ObsidianIntegration(
            vault_path=Path.home() / "Documents" / "Obsidian Vault"  # type: ignore
        )
        self.mem0 = Mem0Integration()
        
        self.output_dir = Path(output_dir)
    
    def download_with_enhancements(
        self,
        model_id: str,
        version_id: str = None,  # type: ignore
        backup_to_drive: bool = False,
        create_note: bool = True,
        save_to_memory: bool = True
    ) -> dict:
        """
        拡張機能付きでモデルをダウンロード
        
        Args:
            model_id: モデルID
            version_id: バージョンID（オプション）
            backup_to_drive: Google Driveにバックアップするか
            create_note: Obsidianにノートを作成するか
            save_to_memory: Mem0にメモリを保存するか
            
        Returns:
            実行結果の辞書
        """
        result = {
            "model_id": model_id,
            "download_success": False,
            "backup_success": False,
            "note_created": False,
            "memory_saved": False
        }
        
        # モデル情報を取得
        model_info = self.civitai.get_model_info(model_id)  # type: ignore
        if not model_info:
            result["error"] = "モデル情報の取得に失敗"
            return result
        
        model_name = model_info.get("name", f"model_{model_id}")
        model_stats = self.civitai.get_model_stats(model_id)  # type: ignore
        
        # ダウンロード実行
        print(f"\n{'='*60}")
        print(f"モデル: {model_name} (ID: {model_id})")
        print(f"{'='*60}")
        
        download_success = self.downloader.download_model(model_id, version_id)
        result["download_success"] = download_success
        
        if not download_success:
            result["error"] = "ダウンロードに失敗"
            return result
        
        # Google Driveにバックアップ
        if backup_to_drive and self.drive.is_available():
            print("\nGoogle Driveにバックアップ中...")
            # ダウンロードされたファイルを探す
            model_files = list(self.output_dir.glob(f"*{model_id}*"))
            for model_file in model_files:
                if model_file.suffix in [".safetensors", ".ckpt"]:
                    file_id = self.drive.upload_file(
                        str(model_file),
                        file_name=model_file.name
                    )
                    if file_id:
                        result["backup_success"] = True
                        result["drive_file_id"] = file_id
                        print(f"バックアップ完了: {file_id}")
                    break
        
        # Obsidianにノート作成
        if create_note and self.obsidian.is_available():
            print("\nObsidianにノート作成中...")
            note_content = f"""# {model_name}

## モデル情報

- **モデルID**: {model_id}
- **名前**: {model_name}
- **ダウンロード数**: {model_stats.get('download_count', 0)}
- **評価**: {model_stats.get('rating', 0)}/5 ({model_stats.get('rating_count', 0)}件)
- **バージョン数**: {model_stats.get('version_count', 0)}

## タグ

{', '.join([f'#{tag}' for tag in model_stats.get('tags', [])])}

## 説明

{model_stats.get('description', '説明なし')[:500]}

## ダウンロード情報

- **ダウンロード日時**: {self._get_current_timestamp()}
- **保存先**: {self.output_dir}
"""
            
            note_path = self.obsidian.create_note(
                title=f"{model_name} - CivitAI",
                content=note_content,
                tags=["CivitAI", "モデル", "ManaOS"] + model_stats.get('tags', [])[:5],
                folder="CivitAI Models"
            )
            
            if note_path:
                result["note_created"] = True
                result["note_path"] = str(note_path)
                print(f"ノート作成完了: {note_path}")
        
        # Mem0にメモリ保存
        if save_to_memory and self.mem0.is_available():
            print("\nMem0にメモリ保存中...")
            memory_text = f"{model_name} (ID: {model_id})をダウンロードしました。評価: {model_stats.get('rating', 0)}/5、ダウンロード数: {model_stats.get('download_count', 0)}"
            memory_id = self.mem0.add_memory(
                memory_text=memory_text,
                user_id="mana",
                metadata={
                    "type": "civitai_model",
                    "model_id": model_id,
                    "model_name": model_name,
                    "download_count": model_stats.get('download_count', 0),
                    "rating": model_stats.get('rating', 0)
                }
            )
            
            if memory_id:
                result["memory_saved"] = True
                result["memory_id"] = memory_id
                print(f"メモリ保存完了: {memory_id}")
        
        return result
    
    def search_and_download(
        self,
        query: str,
        limit: int = 5,
        min_rating: float = 4.0,
        min_downloads: int = 1000
    ) -> list:
        """
        モデルを検索してダウンロード
        
        Args:
            query: 検索クエリ
            limit: 取得数
            min_rating: 最小評価
            min_downloads: 最小ダウンロード数
            
        Returns:
            ダウンロード結果のリスト
        """
        print(f"\nモデル検索: '{query}'")
        models = self.civitai.search_models(query=query, limit=limit)
        
        results = []
        for model in models:
            model_id = str(model.get("id"))
            rating = model.get("rating", 0)
            downloads = model.get("downloadCount", 0)
            
            # フィルタリング
            if rating < min_rating or downloads < min_downloads:
                continue
            
            print(f"\n候補: {model.get('name')} (評価: {rating}/5, DL: {downloads})")
            
            result = self.download_with_enhancements(
                model_id=model_id,
                backup_to_drive=False,  # 大量ダウンロード時はバックアップをスキップ
                create_note=True,
                save_to_memory=True
            )
            results.append(result)
        
        return results
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="拡張CivitAIダウンローダー")
    parser.add_argument("--model-id", type=str, help="モデルID")
    parser.add_argument("--search", type=str, help="検索クエリ")
    parser.add_argument("--backup", action="store_true", help="Google Driveにバックアップ")
    parser.add_argument("--output-dir", type=str, default="models", help="出力ディレクトリ")
    
    args = parser.parse_args()
    
    downloader = EnhancedCivitaiDownloader(output_dir=args.output_dir)
    
    if args.model_id:
        # 特定のモデルをダウンロード
        result = downloader.download_with_enhancements(
            model_id=args.model_id,
            backup_to_drive=args.backup
        )
        print(f"\n結果: {result}")
    
    elif args.search:
        # 検索してダウンロード
        results = downloader.search_and_download(query=args.search)
        print(f"\nダウンロード完了: {len(results)}件")
        for result in results:
            status = "✓" if result.get("download_success") else "✗"
            print(f"  {status} {result.get('model_id')}")
    
    else:
        print("使用方法:")
        print("  --model-id <ID>    特定のモデルをダウンロード")
        print("  --search <query>   モデルを検索してダウンロード")
        print("  --backup           Google Driveにバックアップ")


if __name__ == "__main__":
    main()




















