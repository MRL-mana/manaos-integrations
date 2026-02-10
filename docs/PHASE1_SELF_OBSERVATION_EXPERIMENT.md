# フェーズ1：自己観察（振り返り）実験 — 設計 5分カット

**目的**: 証拠を1本取る。「振り返りあり vs なし」で差が出るか、数十対話で判断する。

---

## 1. 仮説（1行）

> 応答後の自己振り返りをONにすると、**会話継続率**と**同一テーマ再訪**が上がる。

---

## 2. 実験条件

| 項目 | 内容 |
|------|------|
| **比較** | 振り返り **ON** vs **OFF**（同一モデル・同一プロンプト基盤） |
| **期間** | 短期（**20〜40ターン**＝10〜20往復×2条件でも可） |
| **対象** | ローカルLLM対話（LM Studio MCP / Cursor 等、既存の対話窓でOK） |

### ⚠️ ON/OFFで「プロンプト条件」以外を完全固定

比較実験で一番壊れるのがここ。ON/OFFで変えてよいのは**振り返り1問の有無だけ**にする。

| 固定する項目 | 備考 |
|--------------|------|
| temperature | 同じ値で固定 |
| top_p / top_k | 同じ値で固定 |
| システムプロンプト | 同一文字列 |
| コンテキスト長・truncate条件 | 同一 |
| stop tokens | 同一 |
| 乱数seed | 可能なら固定 |

ここがズレると「振り返りが効いた」のか「出力がブレた」のか分からなくなる。

---

## 3. 指標（2つだけ）

| 指標 | 定義（機械的に） | 取り方 |
|------|------------------|--------|
| **会話継続率** | **次のユーザー発話があるか**（時間は無視） | ターンNのあと、同じスレッドでユーザーがさらに1発話以上した → 継続。しなかった → 非継続。全ターンで継続数/総ターン数。 |
| **同一テーマ再訪** | **フェーズ1はテーマ数（ユニーク）**：複数スレッドで出現したユニークテーマの個数 | **テーマID** = 1ターン目ユーザー発話からキーワード上位 **N=3** 語（ストップワード除く・ルール固定）。別スレッドで同じ3語が**完全一致**で出たテーマをカウント。ON/OFFでタグ付け基準を変えない。フェーズ2で回数（頻度）を見る。 |

**判定**: ON群で継続率・再訪が**明確に高い**なら「意味あった」と判断。差がなければ「この条件・期間では効果なし」で一旦ストップ可能。

---

## 4. 振り返りの中身（最小）

OFF = 応答生成のみ。
ON = 応答生成の直後に**1回だけ**以下を実行（既存ブログの「思考習慣」の縮小版）。

- **1問**: 「ユーザーはこの返答に満足しそうか？ 1–5で理由付き。」
- **保存**: 上記の回答を **JSON 1行**でログに追記（時刻・ターンID・満足度・理由）。

永続化（Memory / Chroma）は**フェーズ1では不要**。ログファイルに出すだけでよい。

---

## 5. 実装の置きどころ（既存との統合）

- **既存**: MCP / Memory / タスク評価（`unified_orchestrator` の `auto_evaluate`）はそのまま。
- **追加**: 「対話1ターンごと」に動く**振り返りフラグ + 1プロンプト + ログ書き」を1か所にまとめる。
  - 例: LM Studio MCP のツール内で「応答後に `reflection_enabled=true` なら上記1問を叩き、結果を `phase1_reflection.log` に追記」。
  - または Cursor / 対話UI 側で「送信前にセッション設定で ON/OFF を切り替え、応答後に同じ1問を呼ぶ」でも可。

**コード量の目安**: 設定フラグ + プロンプト文字列 + ログ追記で **50〜100行** 想定。

---

## 6. ログフォーマット（証拠用）

**振り返りログ**（`phase1_reflection.log`）: JSONL 1行1エントリ。

ON の例:

```json
{"ts":"2026-01-30T21:12:03+09:00","condition":"on","thread_id":"abc","turn_id":12,"role":"assistant","satisfaction":4,"reason":"繰り返しを避け具体案を提示","user_msg_preview":"先頭30字","model":"qwen3-30b-a3b-2507","temp":0.7,"top_p":0.9,"max_tokens":2048,"system_hash":"...","params_hash":"...","prompt_hash":"..."}
```

OFF の例（satisfaction/reason は null）:

```json
{"ts":"2026-01-30T21:12:04+09:00","condition":"off","thread_id":"abc","turn_id":12,"role":"assistant","satisfaction":null,"reason":null,"user_msg_preview":"先頭30字","model":"qwen3-30b-a3b-2507","temp":0.7,"top_p":0.9,"max_tokens":2048,"system_hash":"...","params_hash":"..."}
```

**会話ログ**もJSONLにし、同じ `thread_id`, `turn_id` で結合できるようにする。後で集計が楽になる。

**thread_id / turn_id の決め方（固定）**

- **thread_id**: セッション開始時に **1回だけ** 決める。UUID を生成して保持するか、外部から渡す（CLI/HTTP param）。**途中で変えない**。同じ会話でも経路で変えると継続率が壊れる。
- **turn_id**: **assistant の出力単位**で振る（ペアリング型）。例：user(turn_id=1) → assistant(turn_id=1) → user(turn_id=2) → assistant(turn_id=2)。集計「アシスタントターン後にユーザー発話があるか」と対応する。
- **turn_id の責務**: **セッション管理層が turn_id を管理**する。user メッセージ受信で `turn_id += 1` し、その `turn_id` を assistant 出力にもそのまま使う（ペア）。実装で散ると一瞬で崩壊するので、1か所で管理する。

**OFF時も reflection.log に1行出す**

OFFのときも `condition=off` の記録を1行出す（`satisfaction=null`, `reason=null`）。「振り返りを実行しなかった」事実がログになる。ONだけ満足度が出てOFFが欠損だと集計・可視化で分岐が増える。

**同一性検証（原因究明用）**

- **system_hash**: システムプロンプトの sha256 先頭16文字。どこがズレたか秒で分かる。
- **params_hash**: temp / top_p / max_tokens / seed を連結して hash。推論設定の揺れ検出用。
- （任意）**toolchain_hash**: MCP経路など。最低でも system_hash があると強い。

| 必須フィールド | 用途 |
|----------------|------|
| ts, condition, thread_id, turn_id | 突合・継続率 |
| model, temp, top_p, max_tokens, system_hash, params_hash | 条件固定の検証 |
| satisfaction, reason, user_msg_preview | 振り返り内容（OFF時は null） |

---

## 7. やらないこと（フェーズ1）

- LoRA / ファインチューニング
- 振り返り結果の Memory やベクトルDBへの永続化
- 複数観点の振り返り（「感情ラベル」「逆の立場」等はフェーズ2以降）
- 常時フル思考習慣（コスト削減はフェーズ2で「低満足度時のみ」等を検討）

---

## 8. Go の基準（実戦仕様・実験開始OK）

- [ ] **thread_id** がセッション内で不変（UUID 1回 or 外部から渡す）
- [ ] **turn_id** が user/assistant で対応付く（ペアリング型：assistant の出力単位で振る）
- [ ] **OFFでも condition=off のログが1行残る**（satisfaction=null, reason=null 推奨）
- [ ] **system_hash** もしくは prompt_hash で同一性検証できる
- [ ] **ON/OFFで変わるのは「振り返り1問」だけ**（temp / top_p / システムプロンプト等は固定）
- [ ] 推論設定（**model, temp, top_p, system_hash, params_hash**）がログに残る
- [ ] **thread_id / turn_id** が振り返りログ・会話ログの両方にある
- [ ] 振り返り ON/OFF を切り替える**設定**が1か所ある
- [ ] 上記2指標を**集計するスクリプト**がワンコマンドで回る（`python phase1_aggregate.py`）
- [ ] **1回まわして `python phase1_aggregate.py` が落ちない**
- [ ] **20ターン以上**のログが ON/OFF それぞれ取れる見込みがある

ここまで満たせば**実験開始OK**。

---

## 8.1 動作確認チェックリスト（30秒）

- [ ] OFFのときに `condition=off` の1行が出る
- [ ] ONのときに `system_hash` / `params_hash` が埋まる
- [ ] `prompt_hash` が `system_hash` と同じ値で出てる（後方互換）
- [ ] stopwords ファイル無しでも集計が落ちない
- [ ] 空ログで `python phase1_aggregate.py` が exit 0

---

## 8.2 ログの JSON スキーマ（契約）

運用中にフィールド増減すると集計が死ぬので、**先に“契約”として固定**する。変更するときは doc と集計スクリプトを同時に更新する。

**振り返りログ**（`phase1_reflection.log`）1行のフィールド一覧：

| フィールド | 型 | 必須 | 備考 |
|------------|-----|------|------|
| ts | string (ISO8601) | ○ | 記録時刻 |
| condition | "on" \| "off" | ○ | 振り返り ON/OFF |
| thread_id | string | ○ | セッション内不変 |
| turn_id | integer | ○ | ペアリング型 |
| role | string | ○ | "assistant" |
| satisfaction | integer \| null | ○ | 1–5。OFF 時は null |
| reason | string \| null | ○ | OFF 時は null |
| user_msg_preview | string | ○ | 先頭30字 |
| model | string | ○ | モデル名 |
| temp | number | ○ | 推論設定 |
| top_p | number | ○ | 推論設定 |
| max_tokens | integer | ○ | 推論設定 |
| system_hash | string | ○ | sha256 先頭16文字 |
| params_hash | string | ○ | 推論設定の hash |
| prompt_hash | string | ○ | 後方互換。system_hash と同値 |
| request_id | string | △ | 各API呼び出しUUID。プロセス再起動後も突合可能 |
| reflection_status | string | △ | "on" \| "off" \| "failed_parse" \| "failed_call"。本当のOFFと失敗を区別 |
| user_msg_len | integer | △ | ユーザー発話文字数。短文でテーマ再訪が測れない説明用 |
| run_id | string | △ | 任意。実験セッションID（env: PHASE1_RUN_ID） |
| git_commit | string | △ | 任意。ON 時は自動取得可 |
| seed | integer | △ | 任意。推論 seed |

**会話ログ**（`phase1_conversation.log`）1行のフィールド一覧：

| フィールド | 型 | 必須 | 備考 |
|------------|-----|------|------|
| ts | string (ISO8601) | ○ | 記録時刻 |
| thread_id | string | ○ | 振り返りログと突合 |
| turn_id | integer | ○ | 振り返りログと突合 |
| role | "user" \| "assistant" | ○ | |
| content_preview | string | ○ | 先頭200字 |
| request_id | string | △ | 振り返りログと突合用 |

---

## 8.3 運用の最終チェックリスト（10分）

- [ ] **PHASE1_REFLECTION=off** で 3往復 → conversation.log に user/assistant が増える。reflection.log は condition=off の1行/ターン。
- [ ] **PHASE1_REFLECTION=on** で 3往復 → reflection.log に on / failed_parse / failed_call が混ざってもOK。reflection_status で区別できる。
- [ ] 同じ **thread_id** を送り続けると **turn_id** が 1, 2, 3… と増える。
- [ ] **python phase1_aggregate.py** が落ちずに数値を出す。
- [ ] API再起動後に thread_id 継続しても動く（turn_id は in-memory でズレるが、**request_id** で突合可能）。

**OFF 3往復後に追加で見る2点（一瞬で確認可）**

- [ ] **A) request_id の一意性**: 3回とも別の UUID。かつ同じ request_id が conversation.log と reflection.log の両方に出ている → 突合が保証される。
- [ ] **B) prompt_hash の固定**: OFF 3往復の reflection.log（condition=off 行）で `prompt_hash` が全ターン同じ → 条件固定の監査OK。揺れてたら比較実験が壊れる可能性あり。

**OFF 3往復後の集計の目安**

- 会話ログ: 6 行前後（user 3 + assistant 3）
- 振り返りログ: 3 行前後（assistant ターン数ぶん、condition=off）
- 会話継続率: **2/3** が自然（assistant(1)(2)のあとに user あり、assistant(3)のあとは止めた → continued=2, total=3）。0% や 100% に張り付くなら集計ロジックかログ構造のズレを疑う。

**OFF 3往復でよくある事故トップ4（先に回避）**

1. **クライアントが thread_id を返してない** → 3往復のつもりが 3スレッドになる。継続率・再訪が壊れる。**回避**: レスポンスの thread_id を必ず次リクエストで返す（Body か X-Thread-Id）。
2. **「3往復」の定義のズレ** → 継続率 2/3 にしたいなら、止め方は「user1→assistant1, user2→assistant2, user3→assistant3 で止める」。assistant1,2 は続いた、assistant3 は続かない → 2/3 が自然。
3. **reflection.log が OFF でも書かれない** → phase1_enabled() が False のときに log_turn_assistant を呼んでいない設計だと OFF 行が出ない。**回避**: /api/llm/chat で OFF でも phase1 ブロックに入り log_turn_assistant(..., reflection_status="off") が呼ばれているか確認。ドキュと一致させる。
4. **prompt_hash が揺れる** → system prompt に日時・ランダム文字列が混ざる、ルータが内部で system prompt を変える等。**回避**: OFF 時の prompt_hash 固定チェックを必ず見る。揺れてたらフェーズ1の前に直す。

**貼られた集計の判定基準（即チェック）**

- 継続率が 2/3 近いか（0% / 100% 張り付きじゃないか）
- total_turns が 3 になっているか（assistant ターンが 3）
- スレッドが 1 つで回っている気配があるか（thread_id 固定前提）
- reflection.log の condition=off が 3 つ相当あるか
- failed 系が出ていないか（OFF なら出ないのが自然）

貼り付け時、余力があれば「会話ログ行数」「振り返りログ行数」を別行で書くと判定が秒速になる。例：先頭に `conversation_lines=??` / `reflection_lines=??` の2行を置く。

**集計結果が来たら即こう判定する（フェーズ1・OFF 3往復）**

| パターン | 条件 | 判定 | 次の手 |
|----------|------|------|--------|
| **✅ 1. 理想** | 会話ログ 6行前後、振り返りログ 3行前後（off）、継続率 2/3、total_turns=3 | 計測OK | ON 10〜20往復へ |
| **⚠️ 2. 継続率 0%** | 継続率が 0% に張り付く | thread_id が毎回変わって3スレッド / 集計が assistant 後の user を見つけられてない | thread_id 固定・conversation.log の role 順を確認 |
| **⚠️ 3. 継続率 100%** | 継続率が 100% に張り付く | 最後に user4 を送ってる / 集計の turn 境界の扱い | total_turns が 2 になってないか、最後の assistant の数え方を確認 |
| **⚠️ 4. reflection 0行** | OFF なのに reflection.log が 0 行 | OFF で phase1 ブロックに入らず log_turn_assistant が呼ばれてない / パス・権限 | OFF でも 1 行出す設計なら不整合なので修正 |
| **⚠️ 5. prompt_hash 揺れ** | OFF 3行で prompt_hash が揺れてる | system prompt やルータが毎回変えてる | フェーズ1前に直す。比較実験が崩れる |

---

## 9. 実装テンプレ・データ揺れ対策

- **`phase1_reflection.py`**: 振り返りフラグ・1プロンプト・JSONL追記・`system_hash`/`params_hash`。**薄いラッパ** `log_reflection_on` / `log_reflection_off` で hash 生成を中に閉じ込め、呼び出し漏れを防ぐ。OFF時も condition=off で1行出す。`parse_reflection_answer` で振り返りLLM応答をパース。
- **`phase1_hooks.py`**: ManaOS 統合用の**唯一の入口**。`phase1_reflection` を直接呼ばない。`phase1_experiment_active()`（env: `PHASE1_REFLECTION=on|off` でログ記録有効）、`phase1_enabled()`（env: `PHASE1_REFLECTION=on` のときだけ振り返りLLM呼び出し有効）、`get_thread_id_from_request` / `create_thread_id` / `next_turn_id`（thread_id/turn_id を1か所で管理）、`log_turn_user` / `log_turn_assistant`。
- **`phase1_stopwords.txt`**: テーマID用ストップワード（1行1語）。コード直書きより事故らない。
- **`phase1_aggregate.py`**: 継続率・同一テーマ再訪（**テーマ数＝ユニーク**）をワンコマンドで出す。トークナイズは小文字化・数字捨て・記号除去で固定。
- 環境変数: `PHASE1_REFLECTION_LOG`, `PHASE1_CONVERSATION_LOG`, `PHASE1_STOPWORDS`, **`PHASE1_REFLECTION=off`** でログのみ（OFF条件）、**`PHASE1_REFLECTION=on`** で振り返りも実行（ON条件）。未設定ならフェーズ1自体を無効化（ログを書かない）にできる。
- （任意）ログに `run_id`, `git_commit`, `seed` を入れると原因究明が楽になる。

---

## 10. ManaOS 統合（入口1つ）

- **ルールA**: thread_id / turn_id は **phase1_hooks** で唯一管理（in-memory）。入口が複数あっても同じ管理層を呼ぶ。
- **ルールB**: phase1 は**観測のみ**。応答内容に影響しない。反省文はユーザーに見せない（ログだけ）。
- **フック先**: **unified_api_server の `/api/llm/chat` のみ**。LLM応答生成直後・HTTP返却前にフック。
- **呼び順**: 1) `log_turn_user`（ユーザー入力をログ）→ 2) `router.chat` → 3) 振り返り用LLM呼び出し（ON時・同一 model）→ 4) `log_turn_assistant`（会話ログ + 振り返り1行）。
- **振り返り用 router.chat**: 同一 **model** を明示指定。temp/top_p は現行 `router.chat` が引数で取らないため Ollama デフォルト。本体応答の条件は **system_hash / params_hash** でログに残し監査可能。
- **request_id**: 各API呼び出しで UUID を発行し、会話ログ・振り返りログの両方に付与。プロセス再起動や複数ワーカーで turn_id がズレても突合可能。
- **クライアント**: レスポンスに `thread_id`, `turn_id`, `request_id` を返す。次回以降は Body の `thread_id` またはヘッダ `X-Thread-Id` で送る。

*参照: 自己観察システム三層アーキテクチャ（ブログ）。フェーズ1は「第二層の最小版」のみ。*
