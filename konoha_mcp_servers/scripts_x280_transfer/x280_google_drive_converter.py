#!/usr/bin/env python3
"""
X280 Google Drive PDF変換システム
実際のGoogle DriveフォルダからPDFファイルを取得して変換
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
import fitz  # PyMuPDF
import pdfplumber

class X280GoogleDriveConverter:
    def __init__(self):
        self.service = None
        self.folder_id = "1bJlfAI0QeO4KxPrJ6i38dRI9oeyXPnj8"  # 指定されたフォルダID
        self.output_dir = Path("/home/mana/Desktop/X280_GoogleDrive_変換結果")
        self.output_dir.mkdir(exist_ok=True)
        
        # 認証設定
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.credentials_file = '/root/google_drive_credentials.json'
        self.token_file = '/root/token.json'
        
        print("🚀 X280 Google Drive PDF変換システム初期化")
        print(f"📁 出力先: {self.output_dir}")
        print(f"🔗 フォルダID: {self.folder_id}")
    
    def authenticate_google_drive(self):
        """Google Drive認証"""
        try:
            creds = None
            
            # 既存のトークンファイルがあるかチェック
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
            
            # 有効な認証情報がない場合は再認証
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print("❌ 認証ファイルが見つかりません")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('drive', 'v3', credentials=creds)
            print("✅ Google Drive認証成功")
            return True
            
        except Exception as e:
            print(f"❌ Google Drive認証エラー: {e}")
            return False
    
    def list_pdf_files(self):
        """フォルダ内のPDFファイル一覧を取得"""
        try:
            query = f"'{self.folder_id}' in parents and mimeType='application/pdf'"
            results = self.service.files().list(  # type: ignore[union-attr]
                q=query,
                fields="files(id, name, size, modifiedTime)",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            print(f"📄 発見されたPDFファイル: {len(files)}個")
            
            # ファイル情報を表示
            for i, file in enumerate(files[:10], 1):  # 最初の10個を表示
                size_mb = int(file.get('size', 0)) / (1024 * 1024)
                print(f"  {i}. {file['name']} ({size_mb:.1f}MB)")
            
            if len(files) > 10:
                print(f"  ... 他 {len(files) - 10}個のファイル")
            
            return files
            
        except Exception as e:
            print(f"❌ ファイル一覧取得エラー: {e}")
            return []
    
    def download_pdf_file(self, file_id, filename):
        """PDFファイルをダウンロード"""
        try:
            request = self.service.files().get_media(fileId=file_id)  # type: ignore[union-attr]
            file_content = request.execute()
            
            file_path = self.output_dir / f"downloaded_{filename}"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            print(f"✅ ダウンロード完了: {filename}")
            return file_path
            
        except Exception as e:
            print(f"❌ ダウンロードエラー {filename}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path):
        """PDFからテキストを抽出"""
        try:
            text_data = {}
            
            # PyMuPDFでテキスト抽出
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_data[page_num + 1] = text
            
            doc.close()
            print(f"📝 テキスト抽出完了: {len(text_data)}ページ")
            return text_data
            
        except Exception as e:
            print(f"❌ テキスト抽出エラー: {e}")
            return {}
    
    def extract_tables_from_pdf(self, pdf_path):
        """PDFから表データを抽出"""
        try:
            tables_data = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    if tables:
                        tables_data[page_num] = []
                        for table in tables:
                            # 表をDataFrameに変換
                            df = pd.DataFrame(table[1:], columns=table[0] if table else [])
                            tables_data[page_num].append(df)
            
            print(f"📊 表データ抽出完了: {len(tables_data)}ページ")
            return tables_data
            
        except Exception as e:
            print(f"❌ 表データ抽出エラー: {e}")
            return {}
    
    def create_excel_file(self, pdf_filename, text_data, tables_data):
        """Excelファイルを作成"""
        try:
            excel_filename = pdf_filename.replace('.pdf', '_converted.xlsx')
            excel_path = self.output_dir / excel_filename
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # テキストデータシート
                if text_data:
                    text_df = pd.DataFrame([
                        {'ページ': page, 'テキスト': text}
                        for page, text in text_data.items()
                    ])
                    text_df.to_excel(writer, sheet_name='テキストデータ', index=False)
                
                # 表データシート
                sheet_count = 1
                for page_num, tables in tables_data.items():
                    for i, table_df in enumerate(tables):
                        sheet_name = f'表_P{page_num}_{i+1}'[:31]  # Excelシート名制限
                        table_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        sheet_count += 1
                
                # メタデータシート
                metadata = {
                    '項目': ['変換日時', '元ファイル', 'ページ数', '表数', '処理システム'],
                    '値': [
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        pdf_filename,
                        len(text_data),
                        sum(len(tables) for tables in tables_data.values()),
                        'X280 Google Drive Converter'
                    ]
                }
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='メタデータ', index=False)
            
            print(f"✅ Excelファイル作成完了: {excel_filename}")
            return excel_path
            
        except Exception as e:
            print(f"❌ Excelファイル作成エラー: {e}")
            return None
    
    def process_single_pdf(self, file_info):
        """単一PDFファイルの処理"""
        file_id = file_info['id']
        filename = file_info['name']
        
        print(f"\n🔄 処理開始: {filename}")
        
        # ダウンロード
        pdf_path = self.download_pdf_file(file_id, filename)
        if not pdf_path:
            return False
        
        # テキスト抽出
        text_data = self.extract_text_from_pdf(pdf_path)
        
        # 表データ抽出
        tables_data = self.extract_tables_from_pdf(pdf_path)
        
        # Excelファイル作成
        excel_path = self.create_excel_file(filename, text_data, tables_data)
        
        # 一時ファイル削除
        try:
            pdf_path.unlink()
        except Exception:
            pass
        
        return excel_path is not None
    
    async def process_multiple_pdfs(self, max_files=5):
        """複数PDFファイルの処理"""
        if not self.authenticate_google_drive():
            return False
        
        # PDFファイル一覧取得
        pdf_files = self.list_pdf_files()
        if not pdf_files:
            print("❌ PDFファイルが見つかりません")
            return False
        
        # 最大ファイル数で制限
        files_to_process = pdf_files[:max_files]
        
        print(f"\n🚀 {len(files_to_process)}個のPDFファイルを処理開始")
        
        success_count = 0
        for i, file_info in enumerate(files_to_process, 1):
            print(f"\n📄 処理中 ({i}/{len(files_to_process)}): {file_info['name']}")
            
            if self.process_single_pdf(file_info):
                success_count += 1
                print(f"✅ 成功: {file_info['name']}")
            else:
                print(f"❌ 失敗: {file_info['name']}")
        
        print(f"\n🎉 処理完了: {success_count}/{len(files_to_process)} 成功")
        print(f"📁 出力先: {self.output_dir}")
        
        return success_count > 0

def main():
    print("🌟 X280 Google Drive PDF変換システム")
    print("=" * 60)
    
    converter = X280GoogleDriveConverter()
    
    # 非同期処理で実行
    result = asyncio.run(converter.process_multiple_pdfs(max_files=3))
    
    if result:
        print("\n✅ システム正常完了")
        print("📱 X280デスクトップで結果を確認してください")
    else:
        print("\n❌ システムエラー")

if __name__ == "__main__":
    main()
