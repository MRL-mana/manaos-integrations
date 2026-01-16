# Skills × ManaOS統合方針決定

## ✅ 決定事項

**オプション1（現在のまま）を採用**しました。

日付: 2026-01-13

## 📋 選択された構成

### 構成概要

```
AI（思考・判断） → YAML形式で出力 → スクリプトで処理（CLI実行）
```

Skillsは独立したスクリプトとして使用し、ManaOS統合システム（unified_api_server.pyやmanaos_unified_mcp_server）には統合しない。

### 動作フロー

1. **AIがSkillsファイルを自動参照**
   - Cursorの`.cursor/rules/`に配置されたSkillsファイル（`.mdc`）をAIが自動的に読み込み
   - Skillsの使い方、YAMLフォーマット、処理フローを理解

2. **AIがYAML形式で出力**
   - ユーザーの要求に応じて、適切なSkillのYAMLフォーマットで出力
   - 例: `daily_ops`, `git_ops`, `drive_backup`, `n8n_workflow`

3. **スクリプトで処理**
   - ユーザーまたはAIが`python scripts/apply_skill_*.py <yaml_file>`を実行
   - スクリプトがYAMLを読み込み、実際の処理を実行

4. **結果**
   - Obsidianノート作成、Slack通知、Git操作、n8n操作などが実行される
   - 冪等性キーにより、再実行しても重複しない

## 🎯 選択理由

1. **bun913方式に忠実**
   - 「MCPでやる必要のない業務をSkillsに置き換える」という方針に準拠
   - MCPは使わない（トークン削減）

2. **トークン消費が最小**
   - AIはYAMLを出力するだけ（思考・判断に集中）
   - 機械的な処理はスクリプトが担当

3. **シンプルで効率的**
   - スクリプトは人間でもAIでも実行可能
   - 依存関係が少なく、メンテナンスしやすい

4. **自動的に使用可能**
   - SkillsファイルはCursorに配置済み
   - AIが自動的にSkillsの使い方を理解し、適切な場面でYAML出力を提案・生成

## 📊 実装済みSkills

- ✅ `daily_ops`: 日次運用タスク（Obsidianノート作成、Slack通知）
- ✅ `git_ops`: Git操作（commit, push, pull, tag, status）
- ✅ `drive_backup`: Google Driveバックアップ
- ✅ `n8n_workflow`: n8nワークフロー操作（activate, deactivate, execute, import）

## 🔗 参考

- [Skills README](../skills/README.md)
- [実装ガイド](SKILLS_IMPLEMENTATION_GUIDE.md)
- [統合状況](SKILLS_MANAOS_INTEGRATION_STATUS.md)
- [クイックスタート](SKILLS_QUICK_START.md)
- [bun913さんの記事](https://zenn.dev/bun913/articles/mcp-to-skills-token-reduction)
