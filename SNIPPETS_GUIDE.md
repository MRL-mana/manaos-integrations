# スニペット活用ガイド

VSCodeでManaOS開発を超高速化する8つのコードスニペット。

---

## 📋 利用可能なスニペット一覧

| プレフィックス | 説明 | 用途 |
|---------------|------|------|
| `manaos_health` | ヘルスチェックエンドポイント | サービスの健全性確認API |
| `manaos_init` | サービス初期化テンプレート | 新規サービスの骨組み |
| `manaos_mcp_tool` | MCPツール定義 | MCP Server用のツール実装 |
| `manaos_error` | エラーハンドリング | 統一されたエラー処理 |
| `manaos_endpoint` | REST APIエンドポイント | FastAPI エンドポイント作成 |
| `manaos_autonomous` | 自律チェック関数 | System3の監視機能実装 |
| `manaos_test` | テストケース | pytest形式のユニットテスト |
| `manaos_config` | 設定ローダー | Pydanticベースの設定管理 |

---

## 🚀 基本的な使い方

### 1. スニペットを挿入

```python
# 新しいPythonファイルで
manaos_init [TAB]
```

### 2. プレースホルダーを埋める

```python
# TABキーで次のプレースホルダーに移動
# Shift+TABで前のプレースホルダーに戻る
```

### 3. Escでスニペットモードを終了

---

## 📝 各スニペットの詳細

### 1. `manaos_health` - ヘルスチェックエンドポイント

**用途**: サービスの健全性を確認するためのREST APIエンドポイント

**プレースホルダー**:
- `${1:service_name}` - サービス名
- `${2:1.0.0}` - バージョン番号

**生成コード**:
```python
@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "unified_api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
```

**使用例**:
```
manaos_health [TAB]
unified_api [TAB]
1.0.0 [TAB]
```

---

### 2. `manaos_init` - サービス初期化テンプレート

**用途**: 新しいManaOSサービスを作成する際の基本骨組み

**プレースホルダー**:
- `${1:Service Description}` - サービスの説明
- `${2:Feature 1}` - 機能1
- `${3:Feature 2}` - 機能2
- `${4:Service Name}` - サービス名
- `${5:SERVICE_PORT}` - ポート環境変数名
- `${6:5000}` - デフォルトポート番号

**生成コード**: 約60行の完全なサービステンプレート（FastAPI + uvicorn + ロギング）

**使用例**:
```python
# new_service.py として新規ファイルを作成
manaos_init [TAB]
Task Management API [TAB]
タスク登録 [TAB]
タスク検索 [TAB]
Task Manager [TAB]
TASK_MANAGER_PORT [TAB]
5200 [TAB]
```

---

### 3. `manaos_mcp_tool` - MCPツール定義

**用途**: Model Context Protocol (MCP) のツールを実装

**プレースホルダー**:
- `${1:tool_name}` - ツール名
- `${2:param}` - パラメータ名
- `${3:result}` - 結果変数名
- `${4:process}` - 処理関数

**生成コード**:
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """MCPツール実装"""
    if name == "search_memory":
        query = arguments.get("query")
        
        # ツールロジック
        results = search_database(query)
        
        return [types.TextContent(
            type="text",
            text=json.dumps(results, ensure_ascii=False, indent=2)
        )]
    
    raise ValueError(f"Unknown tool: {name}")
```

---

### 4. `manaos_error` - エラーハンドリング

**用途**: 統一されたエラー処理パターン

**プレースホルダー**:
- `${1:# 処理コード}` - 実行するコード
- `${2:Error in process}` - エラーメッセージ

**生成コード**:
```python
try:
    # データベース接続
    conn = connect_database()
except Exception as e:
    logger.error(
        f"Database connection failed: {str(e)}",
        exc_info=True
    )
    raise HTTPException(
        status_code=500,
        detail=f"Database connection failed: {str(e)}"
    )
```

---

### 5. `manaos_endpoint` - REST APIエンドポイント

**用途**: FastAPIでエンドポイントを定義

**プレースホルダー**:
- `${1|get,post,put,delete|}` - HTTPメソッド（選択式）
- `${2:path}` - パス
- `${3:handler_name}` - ハンドラ名
- `${4:params}` - パラメータ
- `${5:Endpoint description}` - 説明
- `${6:Parameter description}` - パラメータ説明
- `${7:Return description}` - 戻り値説明

**生成コード**:
```python
@app.post("/tasks")
async def create_task(task: TaskCreate):
    """
    新しいタスクを作成
    
    Args:
        task: タスク作成情報
    
    Returns:
        作成されたタスク情報
    """
    logger.info(f"create_task called with: {task}")
    
    try:
        # タスク登録処理
        result = database.insert_task(task)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error in create_task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 6. `manaos_autonomous` - 自律チェック関数

**用途**: System3（自律監視システム）のチェック機能を実装

**プレースホルダー**:
- `${1:check_name}` - チェック名
- `${2:Check description}` - チェックの説明
- `${3:# チェックロジック}` - 実装コード
- `${4:Check passed}` - 成功メッセージ

**生成コード**:
```python
def autonomous_check_database_connection(self) -> dict:
    """
    データベース接続状態を確認
    
    Returns:
        dict: チェック結果 (status, message, details)
    """
    try:
        # チェックロジック
        conn = database.test_connection()
        
        return {
            "status": "ok",
            "check": "database_connection",
            "message": "Database connection is healthy",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "check": "database_connection",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

---

### 7. `manaos_test` - テストケース

**用途**: pytest形式のユニットテストを作成

**プレースホルダー**:
- `${1:test_name}` - テスト名
- `${2:Test description}` - テストの説明
- `${3:# テストデータ準備}` - Arrangeフェーズ
- `${4:# 実行}` - Actフェーズ
- `${5:# 検証}` - Assertフェーズ
- `${6:condition}` - 検証条件
- `${7:Error message}` - エラーメッセージ

**生成コード**:
```python
def test_health_endpoint_returns_success():
    """ヘルスチェックエンドポイントが正常に応答することを確認"""
    # Arrange
    client = TestClient(app)
    
    # Act
    response = client.get("/health")
    
    # Assert
    assert response.status_code == 200, "ステータスコードが200でない"
    assert response.json()["status"] == "healthy", "statusがhealthyでない"
```

---

### 8. `manaos_config` - 設定ローダー

**用途**: Pydanticベースの設定管理クラスを作成

**プレースホルダー**:
- `${1:ServiceConfig}` - 設定クラス名
- `${2:Service configuration}` - 設定の説明
- `${3:service_name}` - サービス名
- `${4:5000}` - ポート番号
- `${5:その他の設定}` - 追加設定の説明
- `${6:api_key}` - 追加フィールド名

**生成コード**:
```python
from pydantic import BaseSettings
from typing import Optional

class UnifiedAPIConfig(BaseSettings):
    """Unified API configuration"""
    
    # サービス基本設定
    service_name: str = "unified_api"
    service_port: int = 9500
    service_host: str = "127.0.0.1"
    
    # 環境設定
    debug: bool = False
    log_level: str = "INFO"
    
    # API連携設定
    openai_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# グローバル設定インスタンス
config = UnifiedAPIConfig()
```

---

## 🎯 実践的な使い方

### シナリオ1: 新規サービスを5分で作成

```python
# 1. new_notification_service.py を作成
# 2. スニペット挿入
manaos_init [TAB]

# 3. プレースホルダーを埋める
Notification Service [TAB]
通知送信 [TAB]
通知履歴取得 [TAB]
Notification API [TAB]
NOTIFICATION_PORT [TAB]
5300 [TAB]

# 4. ヘルスチェック追加（すでに含まれている）
# 5. 実行
python new_notification_service.py
```

**結果**: 完全に動作するFastAPIサービスが完成

---

### シナリオ2: MCPツールを追加

```python
# mcp_server.py にツール追加

# 既存のツール定義の下に
manaos_mcp_tool [TAB]
get_notifications [TAB]
limit [TAB]
notifications [TAB]
fetch_notifications [TAB]
```

---

### シナリオ3: テストを書く

```python
# test_notification_service.py を作成

manaos_test [TAB]
send_notification_returns_id [TAB]
通知送信が正常にIDを返すことを確認 [TAB]
notification = {"title": "Test", "body": "Test message"} [TAB]
result = send_notification(notification) [TAB]
"id" in result [TAB]
result.status_code == 200 [TAB]
IDが返されない [TAB]
```

---

## ⚡ ショートカット

| 操作 | ショートカット |
|------|---------------|
| スニペット一覧を表示 | `Ctrl+Space` |
| 次のプレースホルダー | `Tab` |
| 前のプレースホルダー | `Shift+Tab` |
| スニペットモード終了 | `Esc` |

---

## 🔧 カスタマイズ方法

### スニペットファイルの場所

```
C:\Users\mana4\Desktop\.vscode\python.code-snippets
```

### 新しいスニペットを追加

```json
{
  "My Custom Snippet": {
    "prefix": "manaos_custom",
    "body": [
      "# カスタムコード",
      "${1:placeholder}",
      "$0"
    ],
    "description": "カスタムスニペットの説明"
  }
}
```

### プレースホルダーのルール

- `${1:default}` - 最初のプレースホルダー（デフォルト値付き）
- `${2}` - 2番目のプレースホルダー
- `${1|option1,option2|}` - 選択式プレースホルダー
- `$0` - 最終カーソル位置

---

## 📊 生産性の向上

### Before（スニペットなし）

```python
# 60行のテンプレートを手動で入力
# 時間: 約15分
# エラー: タイプミス、importの漏れ、フォーマットのブレ
```

### After（スニペットあり）

```python
# manaos_init [TAB] → プレースホルダー埋める
# 時間: 約2分
# エラー: ゼロ（事前検証済みのコード）
```

**時間短縮**: 約13分/サービス（約87%削減）

---

## 🎓 ベストプラクティス

### 1. **一貫性を保つ**
すべてのManaOSサービスで同じスニペットを使用することで、コードの一貫性を保つ。

### 2. **段階的に学習**
まず基本の3つから始める:
- `manaos_init`
- `manaos_health`
- `manaos_endpoint`

### 3. **カスタマイズ**
プロジェクト固有のパターンが見つかったら、カスタムスニペットを追加。

### 4. **ドキュメントと併用**
スニペットで骨組みを作り、[VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)のベストプラクティスに従って実装。

---

## 🆘 トラブルシューティング

### Q: スニペットが表示されない

**A:** Python拡張機能が有効か確認

```
Ctrl+Shift+X → "Python" で検索 → インストール済みか確認
```

### Q: プレースホルダーが機能しない

**A:** Tabキーが他の機能にバインドされていないか確認

```
File → Preferences → Keyboard Shortcuts
"Tab" で検索 → "editor.action.inlineSuggest.commit" が優先されている場合は無効化
```

### Q: カスタマイズが反映されない

**A:** VSCodeを再起動

```
Ctrl+Shift+P → "Developer: Reload Window"
```

---

## 📚 関連ドキュメント

- **[VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)** - VSCode完全セットアップ
- **[VSCODE_CHECKLIST.md](VSCODE_CHECKLIST.md)** - 対応状況チェックリスト
- **[QUICKREF.md](QUICKREF.md)** - クイックリファレンス

---

**最終更新**: 2026年2月7日  
**スニペット数**: 8個  
**推定時間短縮**: 10-15分/サービス
