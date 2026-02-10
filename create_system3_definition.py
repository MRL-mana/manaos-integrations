#!/usr/bin/env python3
"""
System 3定義書をObsidianに作成
修正版：Autonomy Level + System 3定義の明文化
"""

import os
from pathlib import Path
from datetime import datetime
from obsidian_integration import ObsidianIntegration


def create_system3_definition():
    """System 3定義書を作成"""

    # Obsidian統合を初期化（OBSIDIAN_VAULT_PATH を優先）
    env_path = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
    vault_path = Path(env_path) if env_path else None
    if not vault_path or not vault_path.exists():
        vault_path = Path.home() / "Documents" / "Obsidian Vault"
    if not vault_path.exists():
        vault_path = Path.home() / "Documents" / "Obsidian"
    if not vault_path.exists():
        vault_path = Path.cwd()

    obsidian = ObsidianIntegration(str(vault_path))

    # System 3定義書の内容（修正版）
    content = f"""# ManaOS System 3: Supervisor Layer

**作成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**状態**: アクティブ
**バージョン**: 1.0.0

---

## 🧠 System 3 とは

**System 3 = メタ認知・自己監視・自律改善レイヤー**

ManaOSの既存機能を「System 3」として再定義した統合スーパーバイザー層。

---

## ❗ System 3に関する重要な定義

System 3は **単一のAIモデルやLLMではない**。

以下の既存コンポーネント群を統合した
**振る舞い・制御・評価のレイヤー定義**である。

- Task Critic
- Learning System
- AutoOptimization
- AutonomySystem
- RAG Memory

モデル更新や自己再学習は行わない。

---

## 🏗️ アーキテクチャ

```
[System 1: 直感的反応]
  ↓
[System 2: 思考・計画]
  ↓
[System 3: 評価・改善] ← ここ
  ├─ 実行結果の評価
  ├─ 成功パターンの抽出
  ├─ 失敗パターンの学習
  └─ 自律的な改善サイクル
```

---

## 🔧 既存コンポーネントとの対応

### ✅ 評価AI（System 3 Core）

**実装**: `Task Critic (5102)`

- 実行結果の評価
- 失敗理由の分析
- 改善提案の生成
- 再試行判定

**役割**: System 3の「評価エンジン」

---

### ✅ 学習システム（System 3 Memory）

**実装**: `Learning System`

- 成功パターンの記録
- 失敗パターンの学習
- パフォーマンス改善の追跡
- 自動最適化ルールの生成

**役割**: System 3の「記憶・学習エンジン」

---

### ✅ 自動最適化（System 3 Optimization）

**実装**: `AutoOptimization`

- パフォーマンス分析
- リソース最適化
- 設定の自動調整
- 改善サイクルの実行

**役割**: System 3の「最適化エンジン」

---

### ✅ 自律システム（System 3 Autonomy）

**実装**: `AutonomySystem`

- 自律的な判断
- 内部メンテナンスの自動実行
- ガードレールの監視
- 安全な範囲での自動改善

**役割**: System 3の「自律実行エンジン」

---

### ✅ 記憶レイヤー（System 3 Episodic Memory）

**実装**: `RAG Memory (5103)`

- 重要度スコアによる記憶
- 重複チェック
- 時系列メモリ
- Obsidian/Notion連携

**役割**: System 3の「エピソード記憶」

---

## 🛂 Autonomy Level（自律権限レベル）

System 3の自律行動は以下のレベルに制限される。

- **Level 0**: 観測のみ（評価・記録）
- **Level 1**: 内部メンテナンス（ログ整理・最適化）
- **Level 2**: 推奨提案（人間承認が必要）
- **Level 3**: 実行（※ 現在は禁止）

**現在の運用レベル**: Level 1

---

## 🎯 System 3 の機能

### 1. メタ認知（Meta-Cognition）

**「自分のシステムを外部視点で評価する」**

- 実行結果の客観的評価
- システム状態の自己診断
- パフォーマンスの自己分析
- 改善余地の自動発見

**実装**: Task Critic + Learning System

---

### 2. 自律改善（Autonomous Improvement）

**「成功パターンを自動的に再利用する」**

- 成功ログのPlaybook化
- 改善提案の自動適用
- 設定の自動調整
- 最適化ルールの自動生成

**実装**: Learning System + AutoOptimization

---

### 3. 内部メンテナンス（Internal Maintenance）

**「安全な範囲で自律的にメンテナンスする」**

- ログの自動整理
- キャッシュの最適化
- パフォーマンス改善
- エラーパターンの学習

**実装**: AutonomySystem（内部メンテナンス限定）

---

### 4. ガードレール（Safety & Limits）

**「破壊的な変更を防ぐ」**

- 自律改善の範囲制限
- 重要な設定の保護
- ロールバック機能
- 承認が必要な変更の検出

**実装**: AutonomySystem（AutonomyLevel制御）

---

## 🚀 起動条件

### 自律改善モードの起動条件

1. **内部メンテナンスタスク**
   - ログ整理
   - キャッシュクリア
   - パフォーマンス分析
   - 学習データの整理

2. **成功パターンの記録**
   - 実行成功時の自動記録
   - Playbookへの自動追加
   - 再利用可能パターンの抽出

3. **失敗パターンの学習**
   - エラーログの分析
   - 改善提案の生成
   - 再試行戦略の最適化

4. **パフォーマンス改善**
   - ボトルネックの検出
   - 自動最適化の実行
   - 設定の自動調整

**重要**: ユーザー設定や重要なデータへの変更は**常に承認が必要**

---

## 📊 成功パターンの再利用ルート

```
実行成功
  ↓
Task Critic で評価
  ↓
Learning System で記録
  ↓
Playbook として昇格
  ↓
次回の類似タスクで自動適用
```

**実装場所**:
- `task_critic.py` → 評価
- `learning_system.py` → 記録
- `auto_optimization.py` → 適用

---

## 🔒 制限事項

### System 3が**自律的に変更できない**もの

- ユーザー設定ファイル
- APIキー・認証情報
- 重要なデータベース
- 外部サービスの設定
- セキュリティ関連の設定

### System 3が**自律的に変更できる**もの

- ログファイル
- キャッシュ
- 一時ファイル
- パフォーマンス設定（範囲内）
- 学習データ

---

## 📈 メトリクス

### System 3の効果測定

- **成功率の向上**: 学習による改善
- **再試行率の低下**: パターン学習による最適化
- **パフォーマンス改善**: 自動最適化の効果
- **エラー率の低下**: 失敗パターンの学習

**監視場所**: `PerformanceAnalytics` + `Learning System`

---

## 🎓 学習サイクル

```
1. 実行
   ↓
2. 評価（Task Critic）
   ↓
3. 記録（Learning System）
   ↓
4. 分析（AutoOptimization）
   ↓
5. 改善（AutonomySystem）
   ↓
6. 適用（次回実行時）
```

---

## 🔗 関連コンポーネント

- [[ManaOS_System2]] - 思考・計画レイヤー
- [[ManaOS_System1]] - 直感的反応レイヤー
- [[Task_Critic]] - 評価エンジン
- [[Learning_System]] - 学習エンジン
- [[Autonomy_System]] - 自律エンジン

---

## 📝 今後の拡張

### Phase 1: 明示的なSystem 3ラベル（完了）

- ✅ 既存機能のSystem 3としての再定義
- ✅ 定義書の作成

### Phase 2: 統合ダッシュボード（計画中）

- System 3の状態可視化
- 学習進捗の表示
- 改善提案の一覧

### Phase 3: 高度な自律改善（将来）

- 強化学習の統合
- 予測的改善
- アンサンブル学習

---

## 💡 重要な気づき

**「聞いてみよう！」って言えた時点で System 3 的思考してる**

- 自分のシステムを
- 外部視点で
- 客観的に評価しにいく

それがもうメタ認知。

**実装はもう走ってる。名前をつけた瞬間、完成するタイプのやつ。**

---

**最終更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Obsidianにノートを作成（Systemフォルダに配置）
    note_path = obsidian.create_note(
        title="ManaOS_System3",
        content=content,
        tags=["ManaOS", "System3", "Supervisor", "Meta-Cognition"],
        folder="ManaOS/System",
    )

    if note_path:
        print(f"✅ System 3定義書を作成しました: {note_path}")
        return note_path
    else:
        print("❌ System 3定義書の作成に失敗しました")
        return None


if __name__ == "__main__":
    create_system3_definition()
