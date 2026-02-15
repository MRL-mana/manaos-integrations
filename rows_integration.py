"""
Rows統合モジュール
Excel × Notion × ChatGPT のようなAIスプレッドシートツールとの統合
API/Webhook連携によるデータ分析・ログ管理・収益管理の自動化
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from manaos_logger import get_logger

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))


DEFAULT_MANAOS_API_URL = os.getenv(
    "MANAOS_INTEGRATION_API_URL",
    f"http://127.0.0.1:{UNIFIED_API_PORT}",
).rstrip("/")

logger = get_logger(__name__)

try:
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requestsライブラリがインストールされていません")


class RowsIntegration:
    """Rows統合クラス"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.rows.com/v1",
        webhook_url: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            api_key: Rows APIキー（環境変数ROWS_API_KEYからも取得可能）
            base_url: Rows APIのベースURL
            webhook_url: RowsからのWebhookを受信するURL（ManaOS側）
        """
        self.api_key = api_key or os.getenv("ROWS_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.webhook_url = webhook_url or os.getenv("ROWS_WEBHOOK_URL")
        self.session = None
        
        if REQUESTS_AVAILABLE and self.api_key:
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
    
    def is_available(self) -> bool:
        """
        Rowsが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return REQUESTS_AVAILABLE and self.api_key is not None and self.session is not None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,  # 3 → 2に削減（通信速度向上）
        retry_delay: float = 0.5  # 1.0 → 0.5に短縮（通信速度向上）
    ) -> Optional[Dict[str, Any]]:
        """
        APIリクエストを実行（リトライ機能付き・最適化済み）
        
        Args:
            method: HTTPメソッド（GET, POST, PUT, DELETE）
            endpoint: APIエンドポイント
            data: リクエストボディ
            params: クエリパラメータ
            max_retries: 最大リトライ回数（デフォルト2）
            retry_delay: リトライ間隔（秒、デフォルト0.5）
            
        Returns:
            APIレスポンス（JSON）
        """
        if not self.is_available():
            logger.error("Rows APIが利用できません")
            return None
        
        import time
        
        # タイムアウト設定（最適化済み）
        timeout = 20.0  # 30秒 → 20秒に短縮
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=timeout
                )
                
                # 429 Too Many Requests の場合はリトライ
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(response.headers.get("Retry-After", retry_delay * (attempt + 1)))
                        logger.warning(f"レート制限に達しました。{retry_after}秒後にリトライします...")
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error("レート制限に達しました。リトライ回数を超えました。")
                        return None
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    logger.warning(f"タイムアウトエラー（試行 {attempt + 1}/{max_retries}）: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"タイムアウトエラー: リトライ回数を超えました")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"接続エラー（試行 {attempt + 1}/{max_retries}）: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"接続エラー: リトライ回数を超えました")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                # 4xxエラーはリトライしない
                if 400 <= response.status_code < 500:
                    logger.error(f"HTTPエラー {response.status_code}: {e}")
                    if response.status_code == 401:
                        logger.error("認証エラー: APIキーを確認してください")
                    elif response.status_code == 404:
                        logger.error("リソースが見つかりません")
                    return None
                # 5xxエラーのみリトライ
                elif attempt < max_retries - 1:
                    logger.warning(f"サーバーエラー {response.status_code}（試行 {attempt + 1}/{max_retries}）: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"サーバーエラー: リトライ回数を超えました")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"リクエストエラー（試行 {attempt + 1}/{max_retries}）: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"Rows APIリクエストエラー: {e}")
                    return None
        
        return None
    
    # ========================================
    # スプレッドシート操作
    # ========================================
    
    def create_spreadsheet(
        self,
        title: str,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        新しいスプレッドシートを作成
        
        Args:
            title: スプレッドシートのタイトル
            description: 説明
            
        Returns:
            作成されたスプレッドシート情報
        """
        data = {"title": title}
        if description:
            data["description"] = description
        
        return self._make_request("POST", "/spreadsheets", data=data)
    
    def get_spreadsheet(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """
        スプレッドシート情報を取得
        
        Args:
            spreadsheet_id: スプレッドシートID
            
        Returns:
            スプレッドシート情報
        """
        return self._make_request("GET", f"/spreadsheets/{spreadsheet_id}")
    
    def list_spreadsheets(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        スプレッドシート一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            スプレッドシート一覧
        """
        result = self._make_request("GET", "/spreadsheets", params={"limit": limit})
        if result and "spreadsheets" in result:
            return result["spreadsheets"]
        return result
    
    def update_cell(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        cell: str,
        value: Union[str, int, float, bool]
    ) -> Optional[Dict[str, Any]]:
        """
        セルの値を更新
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            cell: セル参照（例: "A1"）
            value: セルの値
            
        Returns:
            更新結果
        """
        data = {
            "sheet": sheet_name,
            "cell": cell,
            "value": value
        }
        return self._make_request(
            "PUT",
            f"/spreadsheets/{spreadsheet_id}/cells",
            data=data
        )
    
    def get_cell(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        cell: str
    ) -> Optional[Dict[str, Any]]:
        """
        セルの値を取得
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            cell: セル参照（例: "A1"）
            
        Returns:
            セルの値
        """
        params = {
            "sheet": sheet_name,
            "cell": cell
        }
        return self._make_request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/cells",
            params=params
        )
    
    def get_range(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_ref: str
    ) -> Optional[List[List[Any]]]:
        """
        範囲の値を取得
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            range_ref: 範囲参照（例: "A1:B10"）
            
        Returns:
            範囲の値（2次元配列）
        """
        params = {
            "sheet": sheet_name,
            "range": range_ref
        }
        result = self._make_request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/range",
            params=params
        )
        if result and "values" in result:
            return result["values"]
        return result
    
    def update_range(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_ref: str,
        values: List[List[Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        範囲の値を更新
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            range_ref: 範囲参照（例: "A1:B10"）
            values: 更新する値（2次元配列）
            
        Returns:
            更新結果
        """
        data = {
            "sheet": sheet_name,
            "range": range_ref,
            "values": values
        }
        return self._make_request(
            "PUT",
            f"/spreadsheets/{spreadsheet_id}/range",
            data=data
        )
    
    # ========================================
    # AI機能（自然言語での操作）
    # ========================================
    
    def ai_query(
        self,
        spreadsheet_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        AIに自然言語でクエリを実行
        
        例: "この売上データ、傾向分析してグラフ出して"
        
        Args:
            spreadsheet_id: スプレッドシートID
            query: 自然言語のクエリ（日本語可）
            context: 追加のコンテキスト情報
            
        Returns:
            AIの実行結果
        """
        data = {
            "query": query,
            "spreadsheet_id": spreadsheet_id
        }
        if context:
            data["context"] = context
        
        return self._make_request("POST", "/ai/query", data=data)
    
    def ai_analyze(
        self,
        spreadsheet_id: str,
        analysis_type: str = "trend",
        target_range: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        データ分析をAIに依頼
        
        Args:
            spreadsheet_id: スプレッドシートID
            analysis_type: 分析タイプ（trend, summary, correlation等）
            target_range: 分析対象の範囲（例: "A1:Z100"）
            
        Returns:
            分析結果
        """
        data = {
            "spreadsheet_id": spreadsheet_id,
            "analysis_type": analysis_type
        }
        if target_range:
            data["target_range"] = target_range
        
        return self._make_request("POST", "/ai/analyze", data=data)
    
    def ai_generate_function(
        self,
        spreadsheet_id: str,
        description: str,
        target_cell: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        AIに関数を生成してもらう
        
        Args:
            spreadsheet_id: スプレッドシートID
            description: 関数の説明（自然言語）
            target_cell: 関数を配置するセル（例: "B1"）
            
        Returns:
            生成された関数情報
        """
        data = {
            "spreadsheet_id": spreadsheet_id,
            "description": description
        }
        if target_cell:
            data["target_cell"] = target_cell
        
        return self._make_request("POST", "/ai/generate-function", data=data)
    
    # ========================================
    # Webhook連携
    # ========================================
    
    def setup_webhook(
        self,
        spreadsheet_id: str,
        events: List[str],
        webhook_url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Webhookを設定（RowsからManaOSへの通知）
        
        Args:
            spreadsheet_id: スプレッドシートID
            events: 監視するイベント（例: ["cell_updated", "sheet_created"]）
            webhook_url: Webhook URL（ManaOS側）
            
        Returns:
            Webhook設定情報
        """
        data = {
            "spreadsheet_id": spreadsheet_id,
            "events": events,
            "url": webhook_url
        }
        return self._make_request("POST", "/webhooks", data=data)
    
    def send_to_rows(
        self,
        spreadsheet_id: str,
        data: Dict[str, Any],
        sheet_name: str = "Sheet1",
        append: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        ManaOSからRowsにデータを送信
        
        Args:
            spreadsheet_id: スプレッドシートID
            data: 送信するデータ
            sheet_name: シート名
            append: 末尾に追加するか（Falseの場合は上書き）
            
        Returns:
            送信結果
        """
        if append:
            # 末尾の行を取得
            last_row = self._get_last_row(spreadsheet_id, sheet_name)
            start_row = last_row + 1 if last_row else 1
        else:
            start_row = 1
        
        # データを行形式に変換
        if isinstance(data, dict):
            # 辞書の場合、キーをヘッダー、値をデータ行として追加
            headers = list(data.keys())
            values = [list(data.values())]
        elif isinstance(data, list):
            # リストの場合、そのまま使用
            if data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                values = [list(row.values()) for row in data]
            else:
                headers = None
                values = [data] if not isinstance(data[0], list) else data
        else:
            return None
        
        # ヘッダーを書き込む（初回のみ）
        if start_row == 1 and headers:
            header_range = f"A1:{chr(64 + len(headers))}1"
            self.update_range(
                spreadsheet_id,
                sheet_name,
                header_range,
                [headers]
            )
            start_row = 2
        
        # データを書き込む
        data_range = f"A{start_row}:{chr(64 + len(values[0]))}{start_row + len(values) - 1}"
        return self.update_range(
            spreadsheet_id,
            sheet_name,
            data_range,
            values
        )
    
    def _get_last_row(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """
        シートの最後の行番号を取得
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            
        Returns:
            最後の行番号（データがない場合はNone）
        """
        # 大きな範囲を取得して、実際にデータがある最後の行を探す
        result = self.get_range(spreadsheet_id, sheet_name, "A1:Z1000")
        if not result:
            return None
        
        for i in range(len(result) - 1, -1, -1):
            if any(cell for cell in result[i] if cell):
                return i + 1
        
        return None
    
    # ========================================
    # 外部サービス連携（n8n/ManaOS経由）
    # ========================================
    
    def export_to_slack(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_ref: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        スプレッドシートのデータを要約してSlackに送信
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            range_ref: 範囲（指定しない場合は全データ）
            channel: Slackチャンネル
            
        Returns:
            送信結果
        """
        # データを取得
        if range_ref:
            data = self.get_range(spreadsheet_id, sheet_name, range_ref)
        else:
            data = self.get_range(spreadsheet_id, sheet_name, "A1:Z1000")
        
        if not data:
            return None
        
        # AIで要約を生成
        summary_query = f"この表を要約してSlackに投げて: {json.dumps(data[:10], ensure_ascii=False)}"
        summary_result = self.ai_query(spreadsheet_id, summary_query)
        
        # n8n Webhook経由でSlackに送信（ManaOS統合API経由）
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url and REQUESTS_AVAILABLE:
            try:
                payload = {
                    "action": "slack_send",
                    "channel": channel or "#manaos-notifications",
                    "message": summary_result.get("summary", "データ要約完了") if summary_result else "データ取得完了",
                    "data": data[:10],  # 最初の10行のみ
                    "spreadsheet_id": spreadsheet_id,
                    "timestamp": datetime.now().isoformat()
                }
                response = requests.post(n8n_webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Slackへの送信が完了しました: {spreadsheet_id}")
                return {"status": "success", "summary": summary_result}
            except Exception as e:
                logger.warning(f"Slack送信エラー: {e}")
                return None
        
        return summary_result
    
    def sync_with_notion(
        self,
        spreadsheet_id: str,
        notion_database_id: str,
        mapping: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        RowsのデータをNotionデータベースと同期
        
        Args:
            spreadsheet_id: スプレッドシートID
            notion_database_id: NotionデータベースID
            mapping: カラムマッピング（例: {"A": "Name", "B": "Price"}）
            
        Returns:
            同期結果
        """
        # データを取得
        data = self.get_range(spreadsheet_id, "Sheet1", "A1:Z1000")
        if not data:
            return None
        
        # ManaOS統合API経由でNotionに同期
        manaos_api_url = os.getenv("MANAOS_INTEGRATION_API_URL", DEFAULT_MANAOS_API_URL)
        try:
            payload = {
                "action": "notion_sync",
                "notion_database_id": notion_database_id,
                "data": data,
                "mapping": mapping,
                "spreadsheet_id": spreadsheet_id
            }
            response = requests.post(
                f"{manaos_api_url}/api/rows/sync-notion",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Notion同期が完了しました: {spreadsheet_id}")
            return response.json()
        except Exception as e:
            logger.warning(f"Notion同期エラー: {e}")
            return None
    
    # ========================================
    # 高度な機能（バッチ処理、データ変換、自動同期）
    # ========================================
    
    def batch_update(
        self,
        spreadsheet_id: str,
        updates: List[Dict[str, Any]],
        sheet_name: str = "Sheet1"
    ) -> Optional[Dict[str, Any]]:
        """
        複数のセルを一括更新
        
        Args:
            spreadsheet_id: スプレッドシートID
            updates: 更新リスト [{"cell": "A1", "value": "test"}, ...]
            sheet_name: シート名
            
        Returns:
            更新結果
        """
        if not self.is_available():
            return None
        
        results = []
        for update in updates:
            cell = update.get("cell")
            value = update.get("value")
            if cell and value is not None:
                result = self.update_cell(spreadsheet_id, sheet_name, cell, value)
                if result:
                    results.append({"cell": cell, "status": "success"})
                else:
                    results.append({"cell": cell, "status": "failed"})
        
        return {
            "total": len(updates),
            "success": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }
    
    def import_from_csv(
        self,
        spreadsheet_id: str,
        csv_file_path: str,
        sheet_name: str = "Sheet1",
        has_header: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        CSVファイルからデータをインポート
        
        Args:
            spreadsheet_id: スプレッドシートID
            csv_file_path: CSVファイルのパス
            sheet_name: シート名
            has_header: ヘッダー行があるか
            
        Returns:
            インポート結果
        """
        try:
            import csv
            from pathlib import Path
            
            csv_path = Path(csv_file_path)
            if not csv_path.exists():
                logger.error(f"CSVファイルが見つかりません: {csv_file_path}")
                return None
            
            rows_data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    rows_data.append(row)
            
            if not rows_data:
                return None
            
            # ヘッダーを処理
            if has_header:
                headers = rows_data[0]
                data_rows = rows_data[1:]
            else:
                headers = None
                data_rows = rows_data
            
            # データを送信
            if headers:
                # ヘッダーを書き込む
                header_range = f"A1:{chr(64 + len(headers))}1"
                self.update_range(spreadsheet_id, sheet_name, header_range, [headers])
                start_row = 2
            else:
                start_row = 1
            
            # データを書き込む
            if data_rows:
                data_range = f"A{start_row}:{chr(64 + len(data_rows[0]))}{start_row + len(data_rows) - 1}"
                result = self.update_range(spreadsheet_id, sheet_name, data_range, data_rows)
                
                return {
                    "status": "success",
                    "rows_imported": len(data_rows),
                    "has_header": has_header
                }
            
            return None
        except Exception as e:
            logger.error(f"CSVインポートエラー: {e}")
            return None
    
    def export_to_csv(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_ref: str,
        output_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        スプレッドシートのデータをCSVにエクスポート
        
        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            range_ref: 範囲（例: "A1:Z100"）
            output_path: 出力ファイルパス
            
        Returns:
            エクスポート結果
        """
        try:
            import csv
            from pathlib import Path
            
            data = self.get_range(spreadsheet_id, sheet_name, range_ref)
            if not data:
                return None
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for row in data:
                    writer.writerow(row)
            
            return {
                "status": "success",
                "rows_exported": len(data),
                "output_path": str(output_file)
            }
        except Exception as e:
            logger.error(f"CSVエクスポートエラー: {e}")
            return None
    
    def auto_sync(
        self,
        spreadsheet_id: str,
        source_data: List[Dict[str, Any]],
        key_column: str,
        sheet_name: str = "Sheet1",
        sync_interval: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        データの自動同期（定期的にデータを更新）
        
        Args:
            spreadsheet_id: スプレッドシートID
            source_data: 同期元データ
            key_column: キーカラム名（重複チェック用）
            sheet_name: シート名
            sync_interval: 同期間隔（秒）
            
        Returns:
            同期結果
        """
        try:
            # 既存データを取得
            existing_data = self.get_range(spreadsheet_id, sheet_name, "A1:Z1000")
            
            if not existing_data:
                # データがない場合は新規作成
                return self.send_to_rows(spreadsheet_id, source_data, sheet_name, append=False)
            
            # ヘッダーを取得
            headers = existing_data[0] if existing_data else []
            key_index = headers.index(key_column) if key_column in headers else None
            
            if key_index is None:
                logger.warning(f"キーカラム '{key_column}' が見つかりません")
                return None
            
            # 既存のキー値を取得
            existing_keys = set()
            for row in existing_data[1:]:
                if len(row) > key_index:
                    existing_keys.add(str(row[key_index]))
            
            # 新規データと更新データを分離
            new_rows = []
            updated_rows = []
            
            for item in source_data:
                key_value = str(item.get(key_column, ""))
                if key_value not in existing_keys:
                    new_rows.append(item)
                else:
                    updated_rows.append(item)
            
            # 新規データを追加
            if new_rows:
                self.send_to_rows(spreadsheet_id, new_rows, sheet_name, append=True)
            
            # 更新データを処理（既存の行を更新）
            if updated_rows:
                # 更新処理（簡易版：全データを再送信）
                self.send_to_rows(spreadsheet_id, source_data, sheet_name, append=False)
            
            return {
                "status": "success",
                "new_rows": len(new_rows),
                "updated_rows": len(updated_rows),
                "total_rows": len(source_data)
            }
        except Exception as e:
            logger.error(f"自動同期エラー: {e}")
            return None
    
    def create_dashboard(
        self,
        spreadsheet_id: str,
        dashboard_config: Dict[str, Any],
        sheet_name: str = "Dashboard"
    ) -> Optional[Dict[str, Any]]:
        """
        ダッシュボードを作成（AIで自動生成）
        
        Args:
            spreadsheet_id: スプレッドシートID
            dashboard_config: ダッシュボード設定
            sheet_name: ダッシュボードシート名
            
        Returns:
            作成結果
        """
        try:
            # ダッシュボードの説明を生成
            description = dashboard_config.get("description", "データ分析ダッシュボード")
            metrics = dashboard_config.get("metrics", [])
            charts = dashboard_config.get("charts", [])
            
            query = f"""
            以下のダッシュボードを作成してください:
            - 説明: {description}
            - メトリクス: {', '.join(metrics)}
            - グラフ: {', '.join(charts)}
            """
            
            result = self.ai_query(spreadsheet_id, query)
            
            return {
                "status": "success",
                "dashboard_sheet": sheet_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"ダッシュボード作成エラー: {e}")
            return None

