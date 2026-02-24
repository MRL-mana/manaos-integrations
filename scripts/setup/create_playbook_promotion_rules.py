#!/usr/bin/env python3
"""
Playbook昇格ルール定義書をObsidianに作成
"""

import os
from pathlib import Path
from datetime import datetime
from obsidian_integration import ObsidianIntegration


def create_playbook_promotion_rules():
    """Playbook昇格ルール定義書を作成"""

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

    content = f"""# Playbook昇格ルール定義（v1.0）

**作成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**状態**: アクティブ
**バージョン**: 1.0.0

---

## 1) 目的

* 成功した手順や判断を「再利用できる資産」に変える
* 再推論・再試行・再調査を減らし、**成功率↑ / コスト↓ / 時間↓** を狙う
* "ログ"を"武器"に昇格させる

---

## 2) 用語

* **Candidate（候補）**：成功したけど、まだ安定性が不明な手順
* **Playbook（正式）**：再利用してよいとSystem 3が判断した標準手順
* **Anti-Playbook（地雷帳）**：やると失敗しやすい/危険な手順（禁止・注意）

---

## 3) 昇格の基本ルール（Gate方式）

Playbook化は **3つのゲート** を通す。

### Gate A：再現性（Reproducibility）

以下のどれかを満たすと通過：

* 同系タスクで **連続2回成功**
  または
* 7日以内に **同カテゴリで成功率80%以上**
  または
* "失敗→修正→成功"の流れが1回でも記録され、**修正点が明確**

✅ 判定材料：`System3_Daily_YYYY-MM-DD.md` / metrics / failures

---

### Gate B：コスト価値（Value）

「再利用する価値」があるか。

* **推論/実行ステップを30%以上削減**できる
  または
* 失敗率を**明確に下げる**（例：Hardタスク成功率が上がる）
  または
* "手順が長い/面倒/忘れやすい"系で、標準化の価値が高い

✅ 判定材料：Task Critic評価、再試行回数、所要時間、APIコスト

---

### Gate C：安全性（Safety）

ここ落ちたら即「候補止まり」or「禁止」。

* APIキー、認証、重要設定を書き換えない
* 外部サービス設定を勝手に変えない
* データ削除・破壊リスクがない
* Autonomy Level 1 の範囲に収まる
  （Level 2以上に触れるなら **Need Approval** 送り）

✅ 判定材料：AutonomySystem判定 + Safetyルール

---

## 4) 昇格ランク（Tier）

Playbookには格をつける。これが運用の事故防止になる。

* **Tier 1（Safe & Common）**
  日常系。誰が使っても安全。自動適用OK（Level 1内）
* **Tier 2（Context Required）**
  条件が揃った時だけ。前提条件チェック必須
* **Tier 3（Human Approval）**
  便利だけど影響が大きい。提案はするが実行は承認必須

---

## 5) 反対側：Anti-Playbook（禁止手順）ルール

以下に該当するものは Playbook化せず **Anti-Playbook** へ。

* 失敗が **2回以上** 連続
* 失敗原因が "環境依存/不安定/再現不能"
* セキュリティや設定変更に触れる
* "たまたま動いた感" が強い

保存先例：`ManaOS/System/AntiPlaybooks/`

---

## 6) 保存フォーマット（テンプレ）

Playbook 1本 = 1ファイル（超重要）

保存先：`ManaOS/System/Playbooks/`

ファイル名例：
`PB_RDP_Reconnect_After_Reboot_v1.md`
`PB_RAG_TopK_Tuning_v1.md`

テンプレ：

```markdown
# Playbook: <TITLE>
**Tier**: 1 / 2 / 3
**Created**: YYYY-MM-DD
**Source**: System3_Daily_YYYY-MM-DD
**Applies To**: <task category / trigger>

## Preconditions（前提条件）
-
## Steps（手順）
1.
2.
3.

## Success Criteria（成功条件）
-
## Rollback（ロールバック）
-
## Risks（注意点）
-
## Notes（学習・理由）
-
```

---

## 7) 自動化の流れ（今すぐ運用できる）

* 日次ログ生成
  → 成功/失敗/提案が出る
  → System 3が **Candidate** を抽出
  → 週1で候補を Gate A/B/C 判定
  → 通ったものだけ Playbooks に昇格
  → 次回類似タスクで参照（再利用）

---

## 8) 実装ステップ

### Phase 1: 定義書作成（完了）

- ✅ Playbook昇格ルール定義書の作成

### Phase 2: Candidate抽出（次）

- 日次ログから `Candidate:` 行を拾って一覧化
- 週1で `Playbook Review` を自動生成（Obsidianノート）
- Gate判定は最初は半自動（Need Approvalへ）

### Phase 3: 自動判定（将来）

- Gate A/B/C の自動判定
- Playbook自動生成
- 再利用時の自動参照

---

## 🔗 関連リンク

- [[ManaOS_System3]] - System 3定義書
- [[System3_Status]] - System 3ステータスダッシュボード
- [[System3_Daily_*]] - 日次ログ

---

**最終更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Obsidianにノートを作成
    note_path = obsidian.create_note(
        title="Playbook_Promotion_Rules",
        content=content,
        tags=["ManaOS", "System3", "Playbook", "Rules"],
        folder="ManaOS/System",
    )

    if note_path:
        print(f"✅ Playbook昇格ルール定義書を作成しました: {note_path}")
        return note_path
    else:
        print("❌ Playbook昇格ルール定義書の作成に失敗しました")
        return None


if __name__ == "__main__":
    create_playbook_promotion_rules()
