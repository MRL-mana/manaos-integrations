# CASTLE-EX 実装ロードマップ ＋ 設計テンプレ（v1.1 → v1.2）

v1.1 で「勝ち/負け」を最短判定し、同じ思想を Layer4/6 に横展開して v1.2 の布石まで打つ。

---

## A) v1.1 を回す：最短で「勝ち/負け」を判定する手順

### 1) v1.1 データ生成（Layer2 +240 確定）

- **構成**: 3テンプレ × 各80件（正40 + 負40）＝ **240**
- **型**: relation / attribute / comparison（correspondence を入れるなら4本で各60でもOK）
- **負例の壊し方（v1.1 は固定）**
  - relation: yes/no 反転（8割）＋ subject 差し替え（2割）
  - attribute: value 差し替え（近いが違う）or slot 反転（高↔低）
  - comparison: 勝者反転（A↔B）のみ
- v1.1 は「脱線系」を増やさない（学習が散るため）。

### 2) バリデータ通過のみ採用

- v1.1 JSONL 生成 → `validator` 実行
- **invalid 0 のファイルだけ** train/eval に送る
- invalid が出たらテンプレ or 生成ロジック修正で止める（学習は回さない）。

### 3) stratified split ＋ template/pair grouping

- **ルール**: `group_key = template_id + ":" + pair_id` でグルーピング → group 単位で train/eval に振り分け
- layer / axis / neg_type はなるべく保つ（最小二乗的に）
- **最低ライン**: 同一 pair_id が割れないこと（comparison は特に割れると評価が甘くなる）

### 4) 学習（追加学習 or 再学習）

- **推奨**: 追加学習（Layer2 の事故修正が主因のため）
- 学習率は控えめ（壊れた分布からの修正なので暴れると危険）

### 5) 再評価：見るべき指標セット（勝ち判定）

- Layer2 `invalid_label_count`: **0 付近**
- Layer2 accuracy: **0.60〜0.75**
- 全体 accuracy: **+5〜+10pt**（Layer2 比率次第）
- negative detection（emotion_mismatch は v1.1 では触らないなら横ばいでOK）

**判定基準（超シンプル）**

| 条件 | 判定 |
|------|------|
| invalid が消えた ＋ Layer2 が 0.6 超えた | **勝ち** |
| invalid が消えたのに Layer2 が 0.4 以下 | モデル/学習量問題の疑い |
| invalid が残る | まだデータ事故 |

---

## サマリ貼付時の判定ルール（即診断用）

貼られた瞬間にこの順で判断する。

### 0) invalid が残ってないか

- **layer2 invalid > 0** → まずデータ事故（テンプレ or 抽出ルール再確認）
- **layer4/6 invalid が急増** → validator が厳しすぎ or テンプレ構造が合ってない

### 1) Layer2 が伸びたか

- **layer2 acc >= 0.60** → Layer2 復活（勝ち）
- **layer2 acc 0.55 未満** → 学習設定 or データ設計側を疑う

### 2) Layer4/6 が落ちてないか

- **layer4/6 が v1.0 比で明確に下がった** → 追加学習で分布が動いた（LR/steps/混ぜ物で安定化）

### 3) Layer2 template 別で「落ちてるやつ」を特定

- **l2_comparison だけ弱い** → 反転負例の比率調整 / metric 語彙拡張
- **l2_attribute だけ弱い** → attr/value 辞書の「近いけど違う」設計を強化
- **l2_relation / part_whole が弱い** → is-a / part-of の関係辞書を整理（曖昧ペアを除外）

---

## v1.2 テンプレ別処方箋（Layer2）

サマリで弱いテンプレが判明した瞬間にこう打つ。

| 弱いテンプレ | 打ち手 |
|-------------|--------|
| **l2_attribute** | 正例：`{obj}の{attr}は{value}` を増やす（value は高/中/低 3段階）。負例：value 反転 8割、attr 差し替え 2割。attr は「危険度/重要度/大きさ/優先度/効率」など似てて混ざりやすいものをあえて入れる。 |
| **l2_comparison** | 正例：`AとBではAの方がmetric` を固定。負例：勝者反転（A↔B）9割。AとBを同カテゴリに縛る（異種比較を減らす）。 |
| **l2_correspondence** | role-task 辞書を「近いけど違う」で二重化（新人/ベテラン、受付/現場など）。負例は task だけ差し替え（role は保持）。 |

---

## Layer4/6 invalid の扱い（v1.2 布石）

- **layer4/6 invalid がほぼ 0** → OK、そのまま増強フェーズへ
- **invalid が増えた** → validator が厳しすぎ。構造語「1つ以上」を緩める or 条件（80文字以上など）を見直す

---

## B) Layer4/6 に横展開：同じ思想で「壊れにくいデータ設計」

### 1) スロットの名前空間化（l4_* / l6_*）

- Layer2 と同様: `{l4_context}` `{l4_constraint}` `{l4_exception}` … / `{l6_context}` `{l6_policy}` `{l6_risk}` `{l6_mitigation}` …
- **狙い**: テンプレを増やしても slot 衝突で死なない。

### 2) 型判定 ＋ 必須語ルール（バリデータ）を Layer4/6 に入れる

**Layer4（おすすめの型）**

- **multi-constraint**: 制約が2つ以上
- **exception**: 例外条件あり
- **stateful**: 前提を保持して次の指示に従う

**必須チェック例**

- question の制約語（「〜しない」「〜のみ」「〜必須」）が answer に反映されているか
- 例外型なら「ただし/例外/しかし」が answer に含まれるか（雑でOK）

**Layer6（おすすめの型）**

- **policy**: 方針・ルールに沿って判断
- **tradeoff**: メリデメ比較して結論
- **risk_mgmt**: 危険/安全/対策が揃っている

**必須チェック例**

- tradeoff なら「メリット/デメリット/結論」のいずれかが揃う
- risk_mgmt なら「リスク ＋ 対策」が揃う
※ 内容の正しさまで判定しない。壊れ検知が目的。

### 3) 評価側にも invalid_label_count を拡張

- Layer4/6 も invalid_label を accuracy から除外
- invalid_reason_counts を stats に入れる
→ 事故時に「Layer6 0.2！？ モデル弱い？」ではなく「validator で missing_constraint で死んでた」と秒速で切り分け可能。

---

## Layer4/6 の v1.2 向けテンプレ案（すぐ増強できる形）

### Layer4 テンプレ（条件分岐1回 ＋ 制約2つ）

- **問い例**: 「AのときはX、BのときはY。さらに“Zは禁止”。どう答える？」
- **正解**: 条件を選び、禁止を守る
- **負例**: 禁止だけ破る（1点突破）、条件だけ間違える（1点突破）

### Layer6 テンプレ（tradeoff ＋ risk）

- **問い例**: 「目的はP。選択肢はAとB。コストと安全性がトレードオフ。おすすめは？」
- **正解**: 結論 ＋ 理由（コスト/安全性）＋ リスク対策
- **負例**: 結論は合っているがリスク対策がない、リスクだけ盛って結論がない

---

## 実行順まとめ（TODO にそのまま使える）

1. v1.1 Layer2 +240 生成（3テンプレ×80）
2. validator 通す（invalid 0 確認）
3. stratified split（template_id ＋ pair_id grouping）
4. 追加学習（LR 控えめ）
5. 同一評価で比較（Layer2 invalid=0 / Layer2 acc>=0.6）
6. 並行で Layer4/6 の以下を実施
   - slot namespace（l4_* / l6_*）
   - 型判定（超雑でOK）
   - 必須語/構造チェック
   - invalid_reason / invalid_label_count を評価へ追加

---

## 実装済み状況（本リポジトリ）

| 項目 | 状態 |
|------|------|
| v1.1 Layer2 +240 生成 | ✅ `run_v11_pipeline.py` / `generate_layer_2_v11()` |
| validator（Layer2 ペアリング） | ✅ `validate_layer2_pairing` |
| stratified split（group_by pair_id） | ✅ `castle_ex_dataset_splitter.py` / `--group-by pair_id` |
| Layer4 l4_* 名前空間 | ✅ `generate_layer_4_data()` で既存 |
| Layer6 l6_* 名前空間 | ✅ `generate_layer_6_data()` で `fill_slots_shared` ＋ l6_* |
| Layer4/6 バリデータ（型＋必須語） | ✅ `validate_layer4_pairing` / `validate_layer6_pairing` |
| Layer4/6 評価の invalid_label | ✅ `_is_invalid_layer4` / `_is_invalid_layer6` ＋ `evaluate_item` で設定 |

### pair_id 欠損時の扱い（split）

- **pair_id がある** → `group_key = pair_id`（同一ペアは同じ側）
- **pair_id が無い** → まず `get_message_hash(messages)`。空のときは `get_item_fallback_key(item)`（item の sha1 先頭12桁）で **1件ごとに別キー** → train/eval に分散し、他層が片側に固まらない。

次に貼るもの（どちらかでOK）:

- **v1.1 の学習ログ**（epoch/steps と Layer 別結果だけ）
- **Layer4/6 のテンプレ一覧**（question / answer_template だけ）

貼れない場合は、上記手順で回した**結果の数字だけ**教えてもらえれば、次の打ち手を最短で決められる。
