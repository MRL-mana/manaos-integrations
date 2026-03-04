#!/usr/bin/env python3
"""
日報PDF→Googleスプレッドシート変換（完全版）
Gemini Vision + Google Sheets API

使い方:
  python3 nippo_to_gsheet.py [PDFファイル]
  python3 nippo_to_gsheet.py [フォルダ] [件数]
"""

import os
import sys
from pathlib import Path
import time
import json

try:
    import fitz
    from PIL import Image
    import google.generativeai as genai
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"❌ ライブラリ不足: {e}")
    sys.exit(1)


class NippoToGSheet:
    """日報PDF→Googleスプレッドシート変換"""
    
    def __init__(self):
        # Gemini初期化
        api_key = os.getenv("GEMINI_API_KEY", "AIzaSyC5SA9-bXkB_nlAux9Fve47HvvDm1jx0Y0")
        genai.configure(api_key=api_key)
        self.gemini = genai.GenerativeModel('gemini-2.5-flash')
        
        # Google Sheets API初期化
        self.sheets_service = None
        self.drive_service = None
        self.folder_id = None
        self.init_google_apis()
    
    def init_google_apis(self):
        """Google APIs初期化"""
        with open('/root/token.json', 'r') as f:
            token_data = json.load(f)
        
        creds = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'])
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        # フォルダ作成
        self.folder_id = self.get_or_create_folder('日報スプレッドシート_2025')
    
    def get_or_create_folder(self, folder_name: str):
        """フォルダ取得/作成"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    
    def pdf_to_images(self, pdf_path: str):
        """PDF→画像（全ページ）"""
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        
        doc.close()
        return images
    
    def flatten_data(self, data):
        """配列をフラット化"""
        flattened = []
        for row in data:
            flat_row = []
            for cell in row:
                # セルが配列やオブジェクトの場合は文字列化
                if isinstance(cell, (list, dict)):
                    flat_row.append(json.dumps(cell, ensure_ascii=False) if cell else "")
                elif cell is None:
                    flat_row.append("")
                else:
                    flat_row.append(str(cell))
            flattened.append(flat_row)
        return flattened
    
    def gemini_extract_table(self, image):
        """Gemini Visionで表抽出"""
        prompt = """
この画像の表を抽出してください。

出力形式（JSON配列のみ）:
[
  ["列1", "列2", "列3", ...],
  ["値1-1", "値1-2", "値1-3", ...],
  ...
]

重要：
- 表の構造をそのまま保持
- 全文字を正確に認識（数値もすべて文字列として）
- 空セルは ""（空文字列）
- セルの値は必ず文字列型
- 配列やオブジェクトは使わない
- JSON配列のみ出力
"""
        
        response = self.gemini.generate_content([prompt, image])
        text = response.text.strip()
        
        if '```' in text:
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()
        
        data = json.loads(text)
        
        # データをフラット化
        return self.flatten_data(data)
    
    def create_spreadsheet(self, all_tables_data, title: str):
        """Googleスプレッドシート作成（複数シート対応）"""
        # スプレッドシート作成（複数シート）
        sheets = []
        for i in range(len(all_tables_data)):
            sheets.append({'properties': {'title': f'ページ{i+1}'}})
        
        spreadsheet = {
            'properties': {'title': title},
            'sheets': sheets
        }
        
        sheet = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = sheet['spreadsheetId']
        
        # フォルダに移動
        self.drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=self.folder_id,
            fields='id, parents'
        ).execute()
        
        # 各ページのデータ書き込み
        for i, table_data in enumerate(all_tables_data, 1):
            body = {'values': table_data}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'ページ{i}!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
        
        # フォーマット適用（1行目を強調）
        try:
            # シートIDを取得
            sheet_metadata = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']
            
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.85, 'green': 0.88, 'blue': 0.95},
                            'textFormat': {'bold': True},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            }]
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
        except requests.RequestException:
            pass  # フォーマット失敗しても続行
        
        # リンク取得
        file = self.drive_service.files().get(
            fileId=spreadsheet_id,
            fields='webViewLink'
        ).execute()
        
        return {
            'id': spreadsheet_id,
            'link': file.get('webViewLink')
        }
    
    def convert(self, pdf_path: str):
        """PDF→Googleスプレッドシート変換（複数ページ対応）"""
        pdf_path = Path(pdf_path)
        
        print(f"\n📄 {pdf_path.name}")
        
        try:
            # 1. 全ページ画像化
            images = self.pdf_to_images(str(pdf_path))
            print(f"   🖼️  {len(images)}ページ画像化OK")
            
            # 2. 各ページをGemini抽出
            all_tables_data = []
            for i, image in enumerate(images, 1):
                print(f"   🤖 ページ{i} Gemini解析中...")
                table_data = self.gemini_extract_table(image)
                
                rows = len(table_data)
                cols = len(table_data[0]) if table_data else 0
                print(f"      ✅ {rows}行 x {cols}列")
                
                all_tables_data.append(table_data)
                
                if i < len(images):
                    time.sleep(1)  # API制限対策
            
            # 3. Googleスプレッドシート作成（複数シート）
            print(f"   ☁️  スプレッドシート作成中（{len(all_tables_data)}シート）...")
            result = self.create_spreadsheet(all_tables_data, pdf_path.stem)
            
            print("   ✅ 完了！")
            print(f"   🔗 {result['link']}\n")
            
            return {'success': True, 'link': result['link']}
            
        except Exception as e:
            print(f"   ❌ エラー: {e}\n")
            return {'success': False}
    
    def batch(self, pdf_dir: str, limit: int = None):
        """一括変換"""
        pdf_dir = Path(pdf_dir)
        pdfs = list(pdf_dir.glob('*.pdf'))[:limit] if limit else list(pdf_dir.glob('*.pdf'))
        
        print(f"\n{'='*60}")
        print("📁 日報PDF→Googleスプレッドシート一括変換")
        print(f"{'='*60}")
        print(f"ファイル数: {len(pdfs)}\n")
        
        results = {'total': len(pdfs), 'success': 0, 'failed': 0, 'links': []}
        
        for i, pdf in enumerate(pdfs, 1):
            print(f"[{i}/{len(pdfs)}]", end=' ')
            result = self.convert(str(pdf))
            
            if result['success']:
                results['success'] += 1
                results['links'].append(result['link'])
            else:
                results['failed'] += 1
            
            if i < len(pdfs):
                time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"✅ 成功: {results['success']}/{results['total']}")
        print(f"❌ 失敗: {results['failed']}")
        print("\n📁 Googleスプレッドシート フォルダ:")
        print(f"   https://drive.google.com/drive/folders/{self.folder_id}")
        print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python3 nippo_to_gsheet.py [PDF]")
        print("  python3 nippo_to_gsheet.py [フォルダ] [件数]")
        sys.exit(1)
    
    converter = NippoToGSheet()
    target = Path(sys.argv[1])
    
    if target.is_file():
        converter.convert(str(target))
    elif target.is_dir():
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        converter.batch(str(target), limit=limit)


if __name__ == '__main__':
    main()

