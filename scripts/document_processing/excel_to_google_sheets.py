#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルをGoogle Sheetsに変換してアップロード
Microsoft ExcelがなくてもGoogle Sheetsで確認可能
"""

import pandas as pd
from pathlib import Path
import sys
from manaos_logger import get_logger, get_service_logger
import time

logger = get_service_logger("excel-to-google-sheets")

# Windowsでのエンコーディング修正（cp932で落ちるのを防ぐ）
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    logger.warning("Google Sheets APIライブラリがインストールされていません")


def excel_to_google_sheets(excel_path: str, spreadsheet_title: str = None) -> str:  # type: ignore
    """
    ExcelファイルをGoogle Sheetsに変換してアップロード
    
    Args:
        excel_path: Excelファイルのパス
        spreadsheet_title: スプレッドシートのタイトル（オプション）
        
    Returns:
        Google SheetsのURL
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        raise ImportError("Google Sheets APIライブラリが必要です")
    
    # 認証
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    creds = None
    token_path = Path("token_sheets.json")
    credentials_path = Path("credentials.json")
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)  # type: ignore[possibly-unbound]
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # type: ignore[possibly-unbound]
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(f"認証情報ファイルが見つかりません: {credentials_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)  # type: ignore[possibly-unbound]
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    # サービスを構築
    sheets_service = build('sheets', 'v4', credentials=creds)  # type: ignore[possibly-unbound]
    drive_service = build('drive', 'v3', credentials=creds)  # type: ignore[possibly-unbound]
    
    # Excelファイルを読み込む
    excel_file = Path(excel_path)
    if not excel_file.exists():
        raise FileNotFoundError(f"Excelファイルが見つかりません: {excel_path}")
    
    print(f"Excelファイルを読み込み中: {excel_file.name}")
    # OCR出力のExcelはヘッダー無し前提のため header=None で読み込む
    # （1行だけのシートが header 扱いで空になるのを防ぐ）
    df_dict = pd.read_excel(excel_path, sheet_name=None, header=None)
    
    # スプレッドシートのタイトル
    if not spreadsheet_title:
        spreadsheet_title = excel_file.stem
    
    # 新しいスプレッドシートを作成
    print(f"Google Sheetsを作成中: {spreadsheet_title}")
    spreadsheet = {
        'properties': {
            'title': spreadsheet_title
        }
    }
    
    spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = spreadsheet['spreadsheetId']
    
    print(f"スプレッドシート作成完了: {spreadsheet_id}")
    
    # 既存のシートを削除（デフォルトのSheet1を除く）
    try:
        spreadsheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet_metadata.get('sheets', []):
            sheet_id = sheet['properties']['sheetId']
            sheet_title = sheet['properties']['title']
            if sheet_title != 'Sheet1':  # Sheet1は残す
                requests_body = {
                    'requests': [{
                        'deleteSheet': {
                            'sheetId': sheet_id
                        }
                    }]
                }
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=requests_body
                ).execute()
    except Exception as e:
        logger.warning(f"既存シートの削除エラー（無視）: {e}")
    
    # 各シートのデータを書き込む
    for idx, (sheet_name, df) in enumerate(df_dict.items()):
        print(f"  シート '{sheet_name}' を書き込み中... ({len(df)}行 × {len(df.columns)}列)")
        
        # シート名をサニタイズ（Google Sheetsの制約に合わせる）
        # 特殊文字を除去、31文字以内に制限
        safe_sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('[', '_').replace(']', '_')
        safe_sheet_name = safe_sheet_name[:31] if len(safe_sheet_name) > 31 else safe_sheet_name
        
        # シートが存在しない場合は作成
        try:
            # シートを作成
            if idx > 0 or safe_sheet_name != 'Sheet1':  # 最初のシートでSheet1でない場合、または2番目以降
                requests_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': safe_sheet_name
                            }
                        }
                    }]
                }
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=requests_body
                ).execute()
        except Exception as e:
            logger.warning(f"シート作成エラー（既に存在する可能性）: {e}")
        
        # データを2次元リストに変換（ヘッダーなし、直接データ）
        values = []
        for _, row in df.iterrows():
            values.append([str(val) if pd.notna(val) else '' for val in row])
        
        # 範囲を指定（A1から開始）
        range_name = f"{safe_sheet_name}!A1"
        
        # データを書き込む
        body = {
            'values': values
        }
        
        try:
            result = sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"    OK {result.get('updatedCells')}セルを更新しました")
            
            # レート制限対策：リクエスト間に待機（1秒）
            time.sleep(1)
            
        except Exception as e:
            error_str = str(e)
            # レート制限エラーの場合
            if '429' in error_str or 'RATE_LIMIT' in error_str or 'Quota exceeded' in error_str:
                print(f"    ⚠️ レート制限に達しました。60秒待機します...")
                time.sleep(60)  # 60秒待機
                # 再試行
                try:
                    result = sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    print(f"    OK {result.get('updatedCells')}セルを更新しました（再試行成功）")
                    time.sleep(1)
                except Exception as e3:
                    logger.error(f"シート '{safe_sheet_name}' の書き込みに失敗（再試行後）: {e3}")
            else:
                logger.error(f"シート '{safe_sheet_name}' の書き込みエラー: {e}")
                # 別の方法を試す（appendを使用）
                try:
                    result = sheets_service.spreadsheets().values().append(
                        spreadsheetId=spreadsheet_id,
                        range=f"{safe_sheet_name}!A1",
                        valueInputOption='RAW',
                        insertDataOption='OVERWRITE',
                        body=body
                    ).execute()
                    print(f"    OK {result.get('updates', {}).get('updatedCells', 0)}セルを更新しました（append方式）")
                    time.sleep(1)
                except Exception as e2:
                    logger.error(f"シート '{safe_sheet_name}' の書き込みに失敗: {e2}")
    
    # URLを生成
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    
    print(f"\n✅ Google Sheets作成完了！")
    print(f"URL: {url}")
    # cp932環境でも落ちないように、絵文字を含まない表示も出す
    print(f"[OK] Google Sheets created. URL: {url}")
    
    return url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python excel_to_google_sheets.py <Excelファイルパス> [スプレッドシートタイトル]")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    spreadsheet_title = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        url = excel_to_google_sheets(excel_path, spreadsheet_title)  # type: ignore
        print("\n[OK] 完了！Google Sheetsで確認できます:")
        print(f"{url}")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
