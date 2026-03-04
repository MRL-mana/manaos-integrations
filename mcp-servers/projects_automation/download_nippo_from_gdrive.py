#!/usr/bin/env python3
"""
Google Driveから日報PDFをダウンロード→Excel変換
フォルダID: 1bJlfAI0QeO4KxPrJ6i38dRI9oeyXPnj8
"""

import os
import sys
from pathlib import Path
import logging

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
except ImportError:
    print("❌ Google APIライブラリが必要です")
    print("   pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/download_nippo_from_gdrive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DownloadNippoFromGDrive")


class GoogleDriveDownloader:
    """Google Drive PDFダウンローダー"""
    
    def __init__(self):
        self.service = None
        self.initialize_drive()
    
    def initialize_drive(self):
        """Google Drive API初期化"""
        try:
            token_path = '/root/token.json'
            
            if not os.path.exists(token_path):
                logger.error("❌ /root/token.jsonが見つかりません")
                sys.exit(1)
            
            # トークンデータ読み込み
            import json
            with open(token_path, 'r') as f:
                token_data = json.load(f)
            
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/drive'])
            )
            
            # トークン更新が必要な場合
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive API接続成功")
            
        except Exception as e:
            logger.error(f"❌ Google Drive初期化エラー: {e}")
            sys.exit(1)
    
    def list_pdf_files(self, folder_id: str):
        """フォルダ内のPDFファイルリストを取得"""
        try:
            logger.info(f"📁 フォルダID: {folder_id} からPDFファイルを検索中...")
            
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, size, modifiedTime)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            
            logger.info(f"✅ PDFファイル {len(files)}個 見つかりました")
            
            return files
            
        except Exception as e:
            logger.error(f"❌ ファイルリスト取得エラー: {e}")
            return []
    
    def download_file(self, file_id: str, file_name: str, output_dir: Path):
        """ファイルをダウンロード"""
        try:
            output_path = output_dir / file_name
            
            # 既にダウンロード済みならスキップ
            if output_path.exists():
                logger.info(f"   ⏭️  スキップ（既存）: {file_name}")
                return {'success': True, 'path': str(output_path), 'skipped': True}
            
            request = self.service.files().get_media(fileId=file_id)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"\r   📥 {file_name}: {progress}%", end='', flush=True)
            
            print()  # 改行
            
            # ファイル保存
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())
            
            file_size = output_path.stat().st_size
            logger.info(f"   ✅ ダウンロード完了: {file_name} ({file_size:,} bytes)")
            
            return {'success': True, 'path': str(output_path), 'skipped': False}
            
        except Exception as e:
            logger.error(f"   ❌ ダウンロードエラー ({file_name}): {e}")
            return {'success': False, 'error': str(e)}
    
    def download_all_pdfs(self, folder_id: str, output_dir: str):
        """フォルダ内の全PDFをダウンロード"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n" + "="*60)
        print("📥 Google Driveから日報PDFダウンロード")
        print("="*60)
        
        # PDFファイルリスト取得
        pdf_files = self.list_pdf_files(folder_id)
        
        if not pdf_files:
            logger.warning("⚠️ PDFファイルが見つかりませんでした")
            return {'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0}
        
        print(f"\n📊 総ファイル数: {len(pdf_files)}")
        print(f"📁 ダウンロード先: {output_dir}\n")
        
        results = {
            'total': len(pdf_files),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'files': []
        }
        
        for i, file_info in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] {file_info['name']}")
            
            result = self.download_file(
                file_id=file_info['id'],
                file_name=file_info['name'],
                output_dir=output_dir
            )
            
            if result['success']:
                if result.get('skipped'):
                    results['skipped'] += 1
                else:
                    results['downloaded'] += 1
            else:
                results['failed'] += 1
            
            results['files'].append({
                'name': file_info['name'],
                'result': result
            })
        
        # サマリー表示
        print(f"\n{'='*60}")
        print("📊 ダウンロード完了サマリー")
        print(f"{'='*60}")
        print(f"   総ファイル数: {results['total']}")
        print(f"   ✅ ダウンロード: {results['downloaded']}")
        print(f"   ⏭️  スキップ: {results['skipped']}")
        print(f"   ❌ 失敗: {results['failed']}")
        print(f"   📁 保存先: {output_dir}")
        print(f"{'='*60}\n")
        
        return results


def main():
    """メイン処理"""
    
    # 日報フォルダID
    NIPPO_FOLDER_ID = '1bJlfAI0QeO4KxPrJ6i38dRI9oeyXPnj8'
    
    # ダウンロード先
    OUTPUT_DIR = '/root/daily_reports/pdf_samples'
    
    # ダウンローダー初期化
    downloader = GoogleDriveDownloader()
    
    # 全PDFダウンロード
    results = downloader.download_all_pdfs(
        folder_id=NIPPO_FOLDER_ID,
        output_dir=OUTPUT_DIR
    )
    
    # 次のステップを表示
    if results['total'] > 0:
        print("🎯 次のステップ:")
        print(f"   python3 /root/nippo_to_excel.py {OUTPUT_DIR}")
        print("\n   ↑ これで全PDFをExcel化できます！\n")


if __name__ == '__main__':
    main()



