# ファイル秘書システム - 実装設計書（詳細版）

**作成日**: 2025-01-28  
**バージョン**: 1.0.0  
**状態**: Phase1実装準備完了

---

## 📋 目次

1. [決定事項（推奨固定）](#決定事項)
2. [Slackコマンド文言テンプレ](#slackコマンド文言テンプレ)
3. [FileRecord JSONスキーマ](#filerecord-jsonスキーマ)
4. [Phase1 API設計](#phase1-api設計)
5. [データベース設計](#データベース設計)
6. [実装順序](#実装順序)

---

## 🎯 決定事項（推奨固定）

### 1. アーカイブ方式
**選択**: **A（実体移動しない）**  
- ファイル本体は動かさず、メタデータ（status）のみ変更
- 検索は常に全ファイル対象（INBOX + ARCHIVE）
- 戻す操作が即座に可能（ファイル移動なし）

### 2. 「終わった」の対象
**選択**: **A（直前スレッド添付ファイル）**  
- そのスレッドに添付されたファイルを優先
- thread_refで紐付け管理
- 対象が曖昧な場合は候補を提示して選択

### 3. 最初に監視する場所
**選択**: **母艦（`00_INBOX/`）**  
- Phase1は母艦のみ
- Phase2でGoogle Drive、Phase3でX280を追加

---

## 💬 Slackコマンド文言テンプレ

### トリガー語彙（実装用）

```python
TRIGGER_COMMANDS = {
    "done": ["終わった", "完了", "done", "おわり"],
    "skip": ["今日は放置", "放置", "skip", "あとで"],
    "status": ["Inboxどう？", "状況", "status", "一覧"],
    "restore": ["戻して", "復元", "restore", "undo"],
    "search": ["探して", "検索", "search", "find"]
}
```

### 返信テンプレート（コピペ用）

#### 1. INBOX新規ファイル検知（自動・任意）

```python
TEMPLATE_NEW_FILES = """INBOXに{count}件入ったよ（{types}）
必要なら「Inboxどう？」で一覧出す"""
```

#### 2. 「Inboxどう？」返信

```python
TEMPLATE_INBOX_STATUS = """INBOX状況：新規{new_count} / 未処理{old_count}（長期{long_term_count}）
ざっくり：{summary}
候補：
{candidates}

A 放置 / B {action_b} / C {action_c}"""
```

**例**:
```
INBOX状況：新規3 / 未処理12（長期7）
ざっくり：日報っぽい5、画像素材4、その他3
候補：
・scan_001.pdf（日報っぽい）
・IMG_1234.png（クーポンっぽい）
・data.xlsx（データっぽい）

A 放置 / B 日報だけ把握 / C 最新3件だけ整理
```

#### 3. 「終わった」実行完了

```python
TEMPLATE_DONE = """整理したよ：{count}件
{file_list}

違ったら「戻して」でOK"""
```

**例**:
```
整理したよ：3件
・`2026-01-03_日報_実績_確定.pdf`（元：scan_001.pdf）
・`2026-01-03_洗車_クーポン_案A.png`（元：IMG_1234.png）
・`2026-01-03_データ_売上_1月.xlsx`（元：data.xlsx）

違ったら「戻して」でOK
```

#### 4. 「戻して」復元完了

```python
TEMPLATE_RESTORE = """復元したよ：{count}件
{file_list}

INBOXに戻したから、また整理できるよ"""
```

#### 5. 「探して：◯◯」検索結果

```python
TEMPLATE_SEARCH = """「{query}」で{count}件見つかったよ
{results}

A 詳細見る / B 整理する / C 放置"""
```

#### 6. エラー・不明なコマンド

```python
TEMPLATE_ERROR = """ごめん、{reason}
使えるコマンド：
・「Inboxどう？」：状況確認
・「終わった」：整理実行
・「戻して」：復元
・「探して：◯◯」：検索"""
```

---

## 📄 FileRecord JSONスキーマ

### 完全版スキーマ

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FileRecord",
  "type": "object",
  "required": ["id", "source", "path", "original_name", "created_at", "status"],
  "properties": {
    "id": {
      "type": "string",
      "description": "ファイルID（SHA256ハッシュまたはUUID）",
      "pattern": "^[a-f0-9]{64}$|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    },
    "source": {
      "type": "string",
      "enum": ["mother", "drive", "x280"],
      "description": "ファイルのソース（母艦/Drive/X280）"
    },
    "path": {
      "type": "string",
      "description": "元のファイルパス（絶対パスまたは相対パス）"
    },
    "original_name": {
      "type": "string",
      "description": "元のファイル名"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "FileRecord作成日時（ISO 8601）"
    },
    "modified_at": {
      "type": "string",
      "format": "date-time",
      "description": "ファイルの最終更新日時（ISO 8601）"
    },
    "file_created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ファイルの作成日時（ISO 8601、可能な場合）"
    },
    "type": {
      "type": "string",
      "enum": ["pdf", "image", "xlsx", "docx", "md", "txt", "other"],
      "description": "ファイルタイプ"
    },
    "size": {
      "type": "integer",
      "minimum": 0,
      "description": "ファイルサイズ（バイト）"
    },
    "hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "ファイルのSHA256ハッシュ（重複検知用）"
    },
    "status": {
      "type": "string",
      "enum": ["inbox", "triaged", "done", "archived"],
      "description": "ファイルの状態"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "タグリスト（例: [\"日報\", \"洗車\", \"クーポン\"]）",
      "default": []
    },
    "alias_name": {
      "type": "string",
      "description": "検索用の人間名（例: 2026-01-03_洗車_クーポン_案A.png）",
      "default": null
    },
    "summary": {
      "type": "string",
      "description": "一行要約（LLM生成または手動）",
      "default": null
    },
    "ocr_text_ref": {
      "type": "string",
      "description": "OCRテキストへの参照（ファイルパスまたはID）",
      "default": null
    },
    "thread_ref": {
      "type": "string",
      "description": "SlackスレッドID（紐付け用）",
      "default": null
    },
    "audit_log": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "timestamp": {
            "type": "string",
            "format": "date-time"
          },
          "action": {
            "type": "string",
            "enum": ["created", "triaged", "tagged", "renamed", "archived", "restored"]
          },
          "user": {
            "type": "string"
          },
          "details": {
            "type": "object"
          }
        },
        "required": ["timestamp", "action"]
      },
      "description": "操作履歴（戻せる根拠）",
      "default": []
    },
    "metadata": {
      "type": "object",
      "description": "追加メタデータ（自由形式）",
      "default": {}
    }
  }
}
```

### Python Dataclass版（実装用）

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class FileSource(str, Enum):
    MOTHER = "mother"
    DRIVE = "drive"
    X280 = "x280"

class FileType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    XLSX = "xlsx"
    DOCX = "docx"
    MD = "md"
    TXT = "txt"
    OTHER = "other"

class FileStatus(str, Enum):
    INBOX = "inbox"
    TRIAGED = "triaged"
    DONE = "done"
    ARCHIVED = "archived"

class AuditAction(str, Enum):
    CREATED = "created"
    TRIAGED = "triaged"
    TAGGED = "tagged"
    RENAMED = "renamed"
    ARCHIVED = "archived"
    RESTORED = "restored"

@dataclass
class AuditLogEntry:
    timestamp: str  # ISO 8601
    action: AuditAction
    user: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FileRecord:
    id: str
    source: FileSource
    path: str
    original_name: str
    created_at: str  # ISO 8601
    status: FileStatus
    modified_at: Optional[str] = None  # ISO 8601
    file_created_at: Optional[str] = None  # ISO 8601
    type: Optional[FileType] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    alias_name: Optional[str] = None
    summary: Optional[str] = None
    ocr_text_ref: Optional[str] = None
    thread_ref: Optional[str] = None
    audit_log: List[AuditLogEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 🔌 Phase1 API設計

### ベースURL
```
http://localhost:5120  # File Secretary Service（新規ポート）
```

### エンドポイント一覧

#### 1. ヘルスチェック

```
GET /health
```

**レスポンス**:
```json
{
  "status": "healthy",
  "service": "File Secretary",
  "version": "1.0.0"
}
```

---

#### 2. INBOX監視開始

```
POST /api/inbox/watch
```

**リクエスト**:
```json
{
  "source": "mother",
  "path": "/root/00_INBOX",
  "enabled": true
}
```

**レスポンス**:
```json
{
  "status": "success",
  "watch_id": "watch_mother_001",
  "source": "mother",
  "path": "/root/00_INBOX",
  "enabled": true
}
```

---

#### 3. ファイル索引作成（自動・手動）

```
POST /api/files/index
```

**リクエスト**:
```json
{
  "source": "mother",
  "path": "/root/00_INBOX/scan_001.pdf",
  "force": false
}
```

**レスポンス**:
```json
{
  "status": "success",
  "file_record": {
    "id": "abc123...",
    "source": "mother",
    "path": "/root/00_INBOX/scan_001.pdf",
    "original_name": "scan_001.pdf",
    "status": "triaged",
    "type": "pdf",
    "created_at": "2026-01-28T10:00:00Z"
  }
}
```

---

#### 4. INBOX状況取得

```
GET /api/inbox/status
```

**クエリパラメータ**:
- `source` (optional): mother/drive/x280
- `status` (optional): inbox/triaged/done/archived
- `days` (optional): 新規判定日数（デフォルト: 1）

**レスポンス**:
```json
{
  "status": "success",
  "summary": {
    "new_count": 3,
    "old_count": 12,
    "long_term_count": 7,
    "by_type": {
      "pdf": 5,
      "image": 4,
      "xlsx": 3
    }
  },
  "candidates": [
    {
      "id": "abc123...",
      "original_name": "scan_001.pdf",
      "type": "pdf",
      "tags": ["日報っぽい"],
      "created_at": "2026-01-28T10:00:00Z"
    }
  ]
}
```

---

#### 5. ファイル整理実行（「終わった」）

```
POST /api/files/organize
```

**リクエスト**:
```json
{
  "targets": ["file_id_1", "file_id_2"],  // 空の場合はthread_refから自動判定
  "thread_ref": "C01234ABCDE",
  "user": "U01234ABCDE",
  "auto_tag": true,
  "auto_alias": true
}
```

**レスポンス**:
```json
{
  "status": "success",
  "organized_count": 2,
  "files": [
    {
      "id": "file_id_1",
      "original_name": "scan_001.pdf",
      "alias_name": "2026-01-03_日報_実績_確定.pdf",
      "tags": ["日報", "実績"],
      "status": "archived"
    }
  ]
}
```

---

#### 6. ファイル復元（「戻して」）

```
POST /api/files/restore
```

**リクエスト**:
```json
{
  "targets": ["file_id_1"],  // 空の場合は直近の整理操作を復元
  "user": "U01234ABCDE"
}
```

**レスポンス**:
```json
{
  "status": "success",
  "restored_count": 1,
  "files": [
    {
      "id": "file_id_1",
      "status": "inbox",
      "restored_from": "archived"
    }
  ]
}
```

---

#### 7. ファイル検索（「探して：◯◯」）

```
GET /api/files/search
```

**クエリパラメータ**:
- `query` (required): 検索クエリ
- `source` (optional): mother/drive/x280
- `status` (optional): inbox/triaged/done/archived
- `limit` (optional): 結果数上限（デフォルト: 10）

**レスポンス**:
```json
{
  "status": "success",
  "count": 3,
  "results": [
    {
      "id": "file_id_1",
      "original_name": "scan_001.pdf",
      "alias_name": "2026-01-03_日報_実績_確定.pdf",
      "path": "/root/00_INBOX/scan_001.pdf",
      "tags": ["日報", "実績"],
      "summary": "1月の実績データ",
      "status": "archived",
      "created_at": "2026-01-03T10:00:00Z"
    }
  ]
}
```

---

#### 8. ファイル詳細取得

```
GET /api/files/{file_id}
```

**レスポンス**:
```json
{
  "status": "success",
  "file_record": {
    // FileRecord完全版
  }
}
```

---

#### 9. Slack統合エンドポイント（Gateway経由）

```
POST /api/slack/handle
```

**リクエスト**:
```json
{
  "text": "Inboxどう？",
  "user": "U01234ABCDE",
  "channel": "C01234ABCDE",
  "thread_ts": "1234567890.123456",
  "files": [
    {
      "id": "F01234ABCDE",
      "name": "scan_001.pdf",
      "url_private": "https://..."
    }
  ]
}
```

**レスポンス**:
```json
{
  "status": "success",
  "response_text": "INBOX状況：新規3 / 未処理12...",
  "response_type": "thread"  // thread/ephemeral
}
```

---

## 🗄️ データベース設計

### SQLiteスキーマ（Phase1）

```sql
-- FileRecordテーブル
CREATE TABLE file_records (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK(source IN ('mother', 'drive', 'x280')),
    path TEXT NOT NULL,
    original_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    modified_at TEXT,
    file_created_at TEXT,
    type TEXT CHECK(type IN ('pdf', 'image', 'xlsx', 'docx', 'md', 'txt', 'other')),
    size INTEGER,
    hash TEXT,
    status TEXT NOT NULL CHECK(status IN ('inbox', 'triaged', 'done', 'archived')),
    tags TEXT,  -- JSON配列
    alias_name TEXT,
    summary TEXT,
    ocr_text_ref TEXT,
    thread_ref TEXT,
    audit_log TEXT,  -- JSON配列
    metadata TEXT,  -- JSONオブジェクト
    created_at_db TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at_db TEXT DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_file_records_source ON file_records(source);
CREATE INDEX idx_file_records_status ON file_records(status);
CREATE INDEX idx_file_records_thread_ref ON file_records(thread_ref);
CREATE INDEX idx_file_records_hash ON file_records(hash);
CREATE INDEX idx_file_records_created_at ON file_records(created_at);

-- 全文検索用（FTS5）
CREATE VIRTUAL TABLE file_records_fts USING fts5(
    id UNINDEXED,
    original_name,
    alias_name,
    summary,
    tags,
    content='file_records',
    content_rowid='rowid'
);
```

---

## 📝 実装順序

### Phase1（最短で気持ちよくなる）

1. **データベース作成**
   - SQLiteスキーマ実装
   - FileRecordモデル実装

2. **Indexer Worker**
   - ファイル監視（watchdog）
   - FileRecord作成
   - ハッシュ計算・重複検知

3. **File Secretary API**
   - 全エンドポイント実装
   - エラーハンドリング

4. **Slack Gateway拡張**
   - コマンド解析
   - テンプレート返信
   - スレッド返信

5. **Organizer Worker**
   - タグ推定（LLM）
   - alias_name生成
   - status更新

6. **統合テスト**
   - Slack → API → DB → 返信のフロー確認

---

## 🔗 統合ポイント

### Intent Router拡張

既存の`IntentType`に以下を追加：

```python
class IntentType(str, Enum):
    # ... 既存 ...
    FILE_MANAGEMENT = "file_management"  # ファイル整理
    FILE_SEARCH = "file_search"  # ファイル検索
    FILE_STATUS = "file_status"  # INBOX状況確認
```

### Unified Orchestrator拡張

`unified_orchestrator.py`に以下を追加：

```python
# ファイル秘書関連のルーティング
if intent_type == "file_management":
    # File Secretary API呼び出し
elif intent_type == "file_search":
    # 検索API呼び出し
elif intent_type == "file_status":
    # 状況取得API呼び出し
```

---

## 📌 次のステップ

1. この設計書をレビュー
2. Phase1実装開始
3. 動作確認・調整
4. Phase2（Drive/X280/OCR）へ拡張

---

**完成条件（再確認）**:
- ✅ Slackで会話できる
- ✅ INBOXに入れたファイルを把握できる
- ✅ 「終わった」で整理が走る
- ✅ 勝手に削除しない / 急かさない / 戻せる


