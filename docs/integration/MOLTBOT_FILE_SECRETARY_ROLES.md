# MoltBot × File Secretary 役割整理

## 概要

MoltBot と File Secretary は連携してファイル整理を実行します。役割を明確にし、一貫したワークフローを提供します。

## 役割分担

| コンポーネント | 役割 | ポート/URL |
|----------------|------|------------|
| **MoltBot Gateway** | Plan 作成・意図判定・実行計画 | 8088 |
| **File Secretary** | ファイル操作実行・分類・タグ付け | 5120 |
| **統合API** | エントリポイント（secretary_file_organize） | 9500 |

## ワークフロー

```
1. ユーザー/MCP: secretary_file_organize(path, intent, user_hint)
       ↓
2. 統合API (9500) → MoltBot Gateway (8088) に Plan 送信
       ↓
3. MoltBot: 意図判定・Plan 作成（list_only / read_only / organize 等）
       ↓
4. MoltBot → File Secretary (5120) に実行依頼（FILE_SECRETARY_URL）
       ↓
5. File Secretary: ファイル移動・分類・タグ付け・エイリアス作成
       ↓
6. 結果を MoltBot → 統合API → ユーザー に返す
```

## 使い分け

| 意図 (intent) | 動作 |
|---------------|------|
| **list_only** | 指定パスの一覧取得のみ。MoltBot は軽い Plan を返す |
| **read_only** | 読み取りのみ。メタデータ取得など |
| **organize** | ファイル整理を実行。File Secretary が実際の操作を行う |

## 前提条件

- **MoltBot Gateway**: `.env` に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088`
- **File Secretary**: `.env` に `FILE_SECRETARY_URL=http://localhost:5120`
- 起動: `start_unified_api_and_moltbot.bat` で統合API + MoltBot を両方起動

## トラブル時

1. `moltbot_health` で MoltBot Gateway の稼働確認
2. `GET /api/file-secretary/health` で File Secretary の稼働確認
3. 秘書ファイル整理が失敗する場合: MoltBot Gateway (8088) がオフラインの可能性

## 関連

- [MOLTBOT_MANAOS_INTEGRATION_DESIGN.md](./MOLTBOT_MANAOS_INTEGRATION_DESIGN.md)
- [WHAT_ELSE_YOU_CAN_DO.md](../guides/WHAT_ELSE_YOU_CAN_DO.md)
