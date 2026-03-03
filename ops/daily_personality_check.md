# ManaOS 日次 人格思想チェック（RPG + 9502）
date: YYYY-MM-DD
operator: [REDACTED]
mode_expected: safe
run_id: (optional)

---

## 0) 自動セルフチェック（必須）
- [ ] 実行コマンド：
  `python tools/personality_self_check.py --config config/personality_principles.yaml --output logs/personality_self_check.latest.json --strict`
- [ ] 結果：pass=__ fail=__ manual=__  exit=__
- [ ] レポート確認：`logs/personality_self_check.latest.json` を開いた
- [ ] fail が 1つでもあれば **ここで中断（fail-closed）**、復旧/調査へ

---

## 1) 手動チェック（manual=7 を運用に落とす）
> 目的：自動判定できない “人間の責任領域” を毎日短時間で確認する

### M1. 人格モードの適正（safe固定）
- [ ] 今日の運用は safe である（experimental/lab/mufufu を使う予定なし）
- [ ] 例外がある場合：理由と対象タスクを書いた（↓）
  - 例外内容：
  - 対象：
  - 影響範囲：
  - ロールバック手順：

### M2. 権限の逸脱チェック（最小権限）
- [ ] Adminキーを日常運用で使用していない
- [ ] Ops/Read-only の境界が崩れていない（共有・直書き・直ログインなし）

### M3. RPG UI からの危険操作ガード（fail-closed）
- [ ] RPG UI に「危険操作の二段階確認」が残っている（無効化されてない）
- [ ] allowlist/disabled 表示が正常（disabled を誤って叩けない）

### M4. 監査ログの“読める状態”維持（可観測性）
- [ ] 直近24hのエラーが追える（request_id / stack trace / 時刻）
- [ ] 「誰が/何を/いつ」実行したかの痕跡がある（操作主体が曖昧じゃない）

### M5. 再現性の劣化チェック（再現性）
- [ ] 重要タスク（例：画像生成）の I/O 契約が変わっていない
- [ ] seed やバージョンなど、再現に必要な情報がログに残っている

### M6. 周辺機能の常時ON化をしていない（拡張性）
- [ ] 常時起動はコア最小（Memory/Router/Unified API/監視）に収まっている
- [ ] ComfyUI/Automation/Gallery などは “必要時のみ” の運用が守れている

### M7. 人間最終責任の確認（高リスク操作）
- [ ] 破壊的操作（削除/上書き/大量変更）は **人間承認の記録** がある
- [ ] もし実施したなら、diff/バックアップ/戻し手順が残っている

---

## 2) 今日の所見（30秒でOK）
- 今日の変化点（設定変更/新機能/停止したもの）：
- ひとこと（不安・気づき・次の改善）：

---

## 3) 異常時のルール（迷ったら止める）
- fail が出たら：**機能追加禁止 / 原因追跡 / ロールバック優先**
- manual が怪しいなら：**safe固定に戻す / 権限見直し / ログ整備**

---

## これをさらに“運用に組み込む”なら（おすすめ）

- 朝イチ cron/systemd で self_check 実行 → Slackに結果送信
- manualは「RPGダッシュボードにチェックボタン7個」でポチポチ化
  - 完了したらこのMarkdownが自動生成されてObsidian/Notionに保存、が最強

---

次の一手（拡張案）：
**manual=7 をUI化して、チェック完了＝運用OKの“認証スタンプ”にする。**
