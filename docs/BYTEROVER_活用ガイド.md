# ByteRover 活用ガイド

ManaOS プロジェクトで ByteRover を日々使いこなすためのメモ。

---

## 1. いつ curate するか（コンテキストを残す）

- **設計・アーキテクチャを決めたあと** → `brv curate "〜の設計方針は…"` または Cursor で「ByteRover にこの方針を curate して」
- **バグ修正・原因の解明が終わったとき** → 再発防止のためパターンや手順を curate
- **新しい API・ライブラリの使い方を確立したとき** → サンプル・注意点を curate
- **チームで合意したルール**（命名、エラー扱い、デプロイ手順など）→ 迷いがなくなるよう curate

**Cursor との連携**: `.cursor/rules/byterover-rules.mdc` により、タスク完了時に **byterover-store-knowledge** でパターンを保存するよう促されます。

---

## 2. いつ query するか（コンテキストを参照する）

- **新規実装を始める前** → 「このプロジェクトの〇〇の実装パターンは？」と query
- **不具合調査** → 「過去に同様のエラー対応は？」と query
- **よく忘れる設定・手順** → 「〇〇のセットアップ手順」「認証まわりの仕様」などで query

**Cursor での使い方**: チャットで「ByteRover のコンテキストを参照して」「このプロジェクトのテスト戦略を教えて」などと書くと、**byterover-retrieve-knowledge** で関連コンテキストを取得してから回答します。

---

## 3. チームと揃える（push / pull）

- **自分の curate をチームに反映** → `brv` 起動 → Console で `/push`
- **他メンバーの curate を取り込む** → `/pull`
- **状態確認** → `/status` で Init・MCP・Context Tree の変更を確認

---

## 4. 運用のコツ

| やること | やり方 |
|----------|--------|
| 手動で curate | `brv` → Console → `/curate 内容` または `brv curate "内容"` |
| 手動で query | `/query "質問"` または `brv query "質問"` |
| ルール更新 | `/connectors` で Cursor 用ルール再生成 |
| スペース切り替え | `/space switch` |

---

## 5. 現在のコンテキスト構成（例）

- `structure/authentication` … API 認証パターン（ManaOS）
- `compliance/` … 監査・セキュリティ・運用
- `design/` … 設計
- `testing/` … テスト戦略・E2E・ベンチマーク など

必要に応じて `/status` で増えたドメインを確認し、query で活用する。

---

**参照**: [ByteRover Quickstart](https://docs.byterover.dev/quickstart) | [CLI Reference](https://docs.byterover.dev/reference/cli-reference)
