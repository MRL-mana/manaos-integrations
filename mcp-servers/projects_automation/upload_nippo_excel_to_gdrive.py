#!/usr/bin/env python3
"""
日報Excel→Google Driveアップロード
変換済みExcelファイルを別フォルダにアップロード
"""

import os
import sys
from pathlib import Path
import logging

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ google-api-python-clientが必要です")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/upload_nippo_excel_to_gdrive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UploadNippoExcelToGDrive")


class GoogleDriveUploader:
    """Google Drive Excel アップローダー"""
    
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
    
    def get_or_create_folder(self, folder_name: str, parent_id: str = None):  # type: ignore
        """フォルダを取得または作成"""
        try:
            # 既存フォルダを検索
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(  # type: ignore[union-attr]
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ 既存フォルダ使用: {folder_name} (ID: {folder_id})")
                return folder_id
            
            # フォルダを作成
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]  # type: ignore
            
            folder = self.service.files().create(  # type: ignore[union-attr]
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ 新規フォルダ作成: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ フォルダ作成エラー: {e}")
            return None
    
    def upload_file(self, file_path: str, folder_id: str):
        """ファイルをGoogle Driveにアップロード"""
        try:
            file_name = os.path.basename(file_path)
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                resumable=True
            )
            
            file = self.service.files().create(  # type: ignore[union-attr]
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'name': file.get('name'),
                'link': file.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"❌ アップロードエラー ({file_name}): {e}")  # type: ignore[possibly-unbound]
            return {'success': False, 'error': str(e)}
    
    def upload_all_excel(self, excel_dir: str, folder_name: str = '日報Excel変換結果'):
        """Excelファイルを一括アップロード"""
        excel_dir = Path(excel_dir)  # type: ignore
        
        if not excel_dir.exists():  # type: ignore
            logger.error(f"❌ ディレクトリが見つかりません: {excel_dir}")
            return
        
        # Excelファイルを取得
        excel_files = list(excel_dir.glob('*.xlsx'))  # type: ignore
        
        if not excel_files:
            logger.error("❌ アップロードするExcelファイルがありません")
            return
        
        print("\n" + "="*60)
        print("📤 日報Excel → Google Driveアップロード")
        print("="*60)
        
        # フォルダ作成
        folder_id = self.get_or_create_folder(folder_name)
        
        if not folder_id:
            logger.error("❌ フォルダ作成に失敗しました")
            return
        
        print(f"\n📁 アップロード先フォルダ: {folder_name}")
        print(f"📊 総ファイル数: {len(excel_files)}\n")
        
        results = {
            'total': len(excel_files),
            'success': 0,
            'failed': 0,
            'links': []
        }
        
        for i, excel_file in enumerate(excel_files, 1):
            print(f"[{i}/{len(excel_files)}] {excel_file.name}")
            
            result = self.upload_file(str(excel_file), folder_id)
            
            if result['success']:
                results['success'] += 1
                results['links'].append(result['link'])
                print("   ✅ アップロード完了")
            else:
                results['failed'] += 1
                print(f"   ❌ アップロード失敗: {result.get('error', '不明')}")
        
        # サマリー表示
        print(f"\n{'='*60}")
        print("📊 アップロード完了サマリー")
        print(f"{'='*60}")
        print(f"   総ファイル数: {results['total']}")
        print(f"   ✅ 成功: {results['success']}")
        print(f"   ❌ 失敗: {results['failed']}")
        
        if results['success'] > 0:
            # フォルダリンクを取得
            folder_info = self.service.files().get(  # type: ignore[union-attr]
                fileId=folder_id,
                fields='webViewLink'
            ).execute()
            
            folder_link = folder_info.get('webViewLink')
            print("\n📁 Google Driveフォルダ:")
            print(f"   {folder_link}")
        
        print(f"{'='*60}\n")
        
        return results


def main():
    """メイン処理"""
    
    # Excelファイルのディレクトリ
    EXCEL_DIR = '/root/daily_reports/excel'
    
    # Google Driveフォルダ名
    FOLDER_NAME = '日報Excel変換結果_2025'
    
    # アップローダー初期化
    uploader = GoogleDriveUploader()
    
    # 全Excelアップロード
    uploader.upload_all_excel(
        excel_dir=EXCEL_DIR,
        folder_name=FOLDER_NAME
    )


if __name__ == '__main__':
    main()



