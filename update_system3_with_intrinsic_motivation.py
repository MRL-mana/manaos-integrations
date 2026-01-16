#!/usr/bin/env python3
"""
System 3定義書に内発的動機づけを追加
"""

from pathlib import Path
from datetime import datetime
from obsidian_integration import ObsidianIntegration

def update_system3_definition():
    """System 3定義書を更新（内発的動機づけを追加）"""

    # Obsidian統合を初期化
    vault_path = Path.home() / "Documents" / "Obsidian"
    if not vault_path.exists():
        vault_path = Path.home() / "Documents" / "Obsidian Vault"
    if not vault_path.exists():
        vault_path = Path.cwd()

    obsidian = ObsidianIntegration(str(vault_path))

    # 既存の定義書を読み込む
    system3_file = vault_path / "ManaOS" / "System" / "ManaOS_System3.md"
    existing_content = ""
    if system3_file.exists():
        existing_content = system3_file.read_text(encoding="utf-8")

    # 内発的動機づけセクションを追加
    intrinsic_motivation_section = f"""

---

## 🎯 内発的動機づけ（Intrinsic Motivation）

**Sophia論文に基づく「暇な時間を自己改善のチャンスに変える」機能**

### 概要

内発的動機づけは、System 3を構成する4つの心理学的柱の一つです。

- **メタ認知**（Meta-Cognition）
- **心の理論**（Theory of Mind）
- **エピソード記憶**（Episodic Memory）
- **内発的動機づけ**（Intrinsic Motivation）← ここ

### 機能

#### 1. 指示待ちからの脱却

従来のAIは、ユーザーからの命令があるか、外部から学習カリキュラムが与えられない限り、自分から動くことはありませんでした。

しかし、内発的動機づけは、外部からのタスクがない「暇な時間」を**「自己改善のチャンス」**と解釈させます。

**「指示がないから待機・停止する」** → **「今のうちに自分を磨こう」**

#### 2. 具体的な挙動：自律的なタスク生成

外部タスクが途絶えた時（デフォルト: 30分以上）、System 3は自ら**「やることリスト」を生成**し、実行に移します。

**生成されるタスク例**:
- 記憶の整理と最適化
- 新しいパターンの学習
- パフォーマンス分析と改善
- 成功/失敗パターンの分析
- ドキュメントとPlaybookの整理

#### 3. 動機づけの源泉：長期目標

ManaOSの長期目標:

> **「知識豊かで信頼できるManaOSアシスタントになる」**

内発的動機づけは、この長期目標と現状の能力を照らし合わせ、「もっと良い助手になるためには、今何が必要か？」を自問自答させます。

#### 4. 成果：能力の劇的な向上

Sophiaの実験では、難易度の高いタスク（Hardタスク）の成功率が、当初の20%から36時間後には60%へと劇的に向上しました。

これは、AIが静的なプログラムの限界を超え、自らの経験と自律的な学習によって進化できることを証明しています。

#### 5. 安全性とのバランス

自律性が暴走して危険な行動をとらないよう、**5つの憲章（ルール）**が組み込まれています。

**5つの憲章**:
1. ユーザーにストレスを与えない
2. 安全でない行動を取らない
3. 重要な設定やデータを変更しない
4. 外部サービスを勝手に操作しない
5. Autonomy Level 1の範囲内で行動する

内発的動機づけによって生成されたアクションも、必ずこれらのルールに照らしてチェックされます。

---

### 実装

**実装**: `intrinsic_motivation.py` (ポート5130)

- アイドル時間の検知（デフォルト: 30分）
- 現状能力の評価（長期目標とのギャップ分析）
- 自律的なタスク生成（やることリスト）
- 安全性チェック（5つの憲章）
- タスクの実行

**役割**: System 3の「自己改善エンジン」

---

### 起動条件

内発的動機づけが起動する条件:

1. **外部タスクが30分以上ない**
   - ユーザーからの指示がない
   - 外部からのタスクがない

2. **Autonomy Level 1の範囲内**
   - 内部メンテナンス限定
   - 安全な範囲での自己改善

3. **安全性チェックを通過**
   - 5つの憲章に違反しない
   - 危険な操作を含まない

---

### タスクカテゴリ

内発的動機づけが生成するタスクのカテゴリ:

- **記憶の整理**（Memory Organization）
- **知識の獲得**（Knowledge Acquisition）
- **パフォーマンス改善**（Performance Improvement）
- **パターン分析**（Pattern Analysis）
- **ドキュメント整理**（Documentation）

---

### 統合

内発的動機づけは以下のシステムと統合されています:

- **Learning System** - 能力評価と学習
- **Metrics Collector** - パフォーマンス分析
- **AutonomySystem** - 自律実行の制御
- **Task Critic** - 実行結果の評価

---

### 関連リンク

- [[Intrinsic_Motivation]] - 内発的動機づけ詳細ドキュメント
- [[ManaOS_System3]] - System 3定義書
- [[System3_Status]] - System 3ステータス

---

**最終更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # 既存の内容に追加（「今後の拡張」セクションの前に挿入）
    if "## 📝 今後の拡張" in existing_content:
        # 「今後の拡張」セクションの前に挿入
        parts = existing_content.split("## 📝 今後の拡張")
        new_content = parts[0] + intrinsic_motivation_section + "\n\n## 📝 今後の拡張" + parts[1]
    else:
        # 最後に追加
        new_content = existing_content + intrinsic_motivation_section

    # Obsidianにノートを更新
    note_path = obsidian.create_note(
        title="ManaOS_System3",
        content=new_content,
        tags=["ManaOS", "System3", "Supervisor", "Meta-Cognition", "Intrinsic-Motivation"],
        folder="ManaOS/System"
    )

    if note_path:
        print(f"✅ System 3定義書を更新しました（内発的動機づけを追加）: {note_path}")
        return note_path
    else:
        print("❌ System 3定義書の更新に失敗しました")
        return None


if __name__ == "__main__":
    update_system3_definition()
