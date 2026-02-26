import { useState } from 'react'
import { difficultyColor } from '../utils.js'
import { fetchJson } from '../api.js'
import Box from './Box.jsx'
import OutputBlock from './OutputBlock.jsx'
import Sparkline from './Sparkline.jsx'

export default function RLView({ rl, apiBase }) {
  const enabled = Boolean(rl?.enabled)
  const obs = rl?.observation || {}
  const evo = rl?.evolution || {}
  const fb = rl?.feedback || {}
  const skills = Array.isArray(rl?.skills) ? rl.skills : []
  const criteria = rl?.scoring_criteria && typeof rl.scoring_criteria === 'object' ? rl.scoring_criteria : {}

  const [taskId, setTaskId] = useState('')
  const [taskDesc, setTaskDesc] = useState('')
  const [taskOut, setTaskOut] = useState('')
  const [busyOp, setBusyOp] = useState('')

  const [liveData, setLiveData] = useState(null)
  const [liveErr, setLiveErr] = useState('')

  const [historyData, setHistoryData] = useState(null)
  const [historyErr, setHistoryErr] = useState('')
  const [analyticsData, setAnalyticsData] = useState(null)
  const [analyticsErr, setAnalyticsErr] = useState('')
  const [replayStats, setReplayStats] = useState(null)
  const [replaySamples, setReplaySamples] = useState(null)
  const [experimentsData, setExperimentsData] = useState(null)
  const [expCompare, setExpCompare] = useState(null)
  const [curriculumData, setCurriculumData] = useState(null)
  const [replayEvalData, setReplayEvalData] = useState(null)
  const [alertsData, setAlertsData] = useState(null)
  const [policyData, setPolicyData] = useState(null)
  const [rewardData, setRewardData] = useState(null)
  const [metaData, setMetaData] = useState(null)

  // Round 8 state
  const [moData, setMoData] = useState(null)
  const [tradeOffData, setTradeOffData] = useState(null)
  const [transferData, setTransferData] = useState(null)
  const [transferSuggestion, setTransferSuggestion] = useState(null)
  const [ensembleData, setEnsembleData] = useState(null)
  const [ensembleDecision, setEnsembleDecision] = useState(null)
  const [diversityData, setDiversityData] = useState(null)

  async function fetchLiveDashboard() {
    if (busyOp) return
    setLiveErr('')
    setBusyOp('live')
    try {
      const r = await fetchJson('/api/rl/dashboard')
      if (r?.ok) {
        setLiveData(r)
      } else {
        setLiveErr(String(r?.error || 'unknown'))
      }
    } catch (e) {
      setLiveErr(String(e?.message || e))
    } finally {
      setBusyOp('')
    }
  }

  async function runTaskBegin() {
    setTaskOut('')
    setBusyOp('begin')
    try {
      const id = taskId.trim() || `task-${Date.now()}`
      const desc = taskDesc.trim() || '(manual)'
      const res = await fetch(`${apiBase}/api/rl/task/begin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: id, description: desc })
      })
      const data = await res.json().catch(() => ({}))
      setTaskOut(JSON.stringify(data, null, 2))
      if (!taskId.trim()) setTaskId(id)
    } catch (e) {
      setTaskOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runTaskEnd(outcome) {
    setTaskOut('')
    setBusyOp('end')
    try {
      const id = taskId.trim()
      if (!id) { setTaskOut('ERR: task_id required'); return }
      const res = await fetch(`${apiBase}/api/rl/task/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: id, outcome })
      })
      const data = await res.json().catch(() => ({}))
      setTaskOut(JSON.stringify(data, null, 2))
    } catch (e) {
      setTaskOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function fetchHistory() {
    if (busyOp) return
    setHistoryErr('')
    setBusyOp('history')
    try {
      const r = await fetchJson('/api/rl/history?limit=20')
      if (r?.ok) setHistoryData(r.entries || [])
      else setHistoryErr(String(r?.error || 'unknown'))
    } catch (e) { setHistoryErr(String(e?.message || e)) }
    finally { setBusyOp('') }
  }

  async function runCleanup() {
    if (busyOp) return
    if (!window.confirm('Staleデータのクリーンアップを実行しますか？')) return
    setBusyOp('cleanup')
    try {
      const r = await fetch(`${apiBase}/api/rl/cleanup`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const d = await r.json().catch(() => ({}))
      setTaskOut(`Cleanup: ${JSON.stringify(d)}`)
    } catch (e) { setTaskOut(`ERR: ${e?.message}`) }
    finally { setBusyOp('') }
  }

  async function runConfigReload() {
    if (busyOp) return
    setBusyOp('reload')
    try {
      const r = await fetch(`${apiBase}/api/rl/config/reload`, { method: 'POST' })
      const d = await r.json().catch(() => ({}))
      setTaskOut(`Config reload: ${JSON.stringify(d)}`)
    } catch (e) { setTaskOut(`ERR: ${e?.message}`) }
    finally { setBusyOp('') }
  }

  async function fetchAnalytics() {
    if (busyOp) return
    setAnalyticsErr('')
    setBusyOp('analytics')
    try {
      const r = await fetchJson('/api/rl/analytics?windows=5,10,20')
      if (r?.ok) setAnalyticsData(r)
      else setAnalyticsErr(String(r?.error || 'unknown'))
    } catch (e) { setAnalyticsErr(String(e?.message || e)) }
    finally { setBusyOp('') }
  }

  async function toggleScheduler(action) {
    if (busyOp) return
    if (!window.confirm(`スケジューラを ${action} しますか？`)) return
    setBusyOp('scheduler')
    try {
      const r = await fetch(`${apiBase}/api/rl/scheduler/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const d = await r.json().catch(() => ({}))
      setTaskOut(`Scheduler ${action}: ${JSON.stringify(d)}`)
    } catch (e) { setTaskOut(`ERR: ${e?.message}`) }
    finally { setBusyOp('') }
  }

  async function fetchReplayStats() {
    if (busyOp) return
    setBusyOp('replay')
    try {
      const r = await fetchJson('/api/rl/replay/stats')
      if (r?.ok) setReplayStats(r)
    } catch (e) { console.warn('fetchReplayStats:', e) }
    finally { setBusyOp('') }
  }

  async function fetchReplaySamples(prioritized = false) {
    if (busyOp) return
    setBusyOp('replay-sample')
    try {
      const r = await fetchJson(`/api/rl/replay/sample?n=8&prioritized=${prioritized}`)
      if (r?.ok) setReplaySamples(r.samples || [])
    } catch (e) { console.warn('fetchReplaySamples:', e) }
    finally { setBusyOp('') }
  }

  async function fetchExperiments() {
    if (busyOp) return
    setBusyOp('experiments')
    try {
      const r = await fetchJson('/api/rl/experiments')
      if (r?.ok) setExperimentsData(r)
      const c = await fetchJson('/api/rl/experiments/compare?min_samples=2')
      if (c?.ok) setExpCompare(c)
    } catch (e) { console.warn('fetchExperiments:', e) }
    finally { setBusyOp('') }
  }

  async function fetchCurriculum() {
    if (busyOp) return
    setBusyOp('curriculum')
    try {
      const r = await fetchJson('/api/rl/curriculum/recommend')
      if (r?.ok !== undefined) setCurriculumData(r)
    } catch (e) { console.warn('fetchCurriculum:', e) }
    finally { setBusyOp('') }
  }

  async function applyCurriculum() {
    if (busyOp) return
    if (!window.confirm('カリキュラムを適用しますか？（設定が変更されます）')) return
    setBusyOp('curriculum_apply')
    try {
      const r = await fetchJson('/api/rl/curriculum/apply', { method: 'POST' })
      if (r?.ok !== undefined) setCurriculumData(r)
    } catch (e) { console.warn('applyCurriculum:', e) }
    finally { setBusyOp('') }
  }

  async function fetchReplayEval() {
    if (busyOp) return
    setBusyOp('replay_eval')
    try {
      const r = await fetchJson('/api/rl/replay/evaluate?sample_size=30&prioritized=true')
      if (r?.ok !== undefined) setReplayEvalData(r)
    } catch (e) { console.warn('fetchReplayEval:', e) }
    finally { setBusyOp('') }
  }

  async function fetchAlerts() {
    if (busyOp) return
    setBusyOp('alerts')
    try {
      const r = await fetchJson('/api/rl/alerts/check', { method: 'POST' })
      if (r?.ok !== undefined) setAlertsData(r)
    } catch (e) { console.warn('fetchAlerts:', e) }
    finally { setBusyOp('') }
  }

  async function fetchPolicy() {
    if (busyOp) return
    setBusyOp('policy')
    try {
      const r = await fetchJson('/api/rl/policy/snapshot')
      if (r?.ok !== undefined) setPolicyData(r)
    } catch (e) { console.warn('fetchPolicy:', e) }
    finally { setBusyOp('') }
  }

  async function fetchPolicyUpdate() {
    if (busyOp) return
    setBusyOp('policyUpdate')
    try {
      const r = await fetchJson('/api/rl/policy/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(10) })
      if (r) setPolicyData((prev) => prev ? { ...prev, _lastUpdate: r } : prev)
    } catch (e) { console.warn('fetchPolicyUpdate:', e) }
    finally { setBusyOp('') }
  }

  async function fetchReward() {
    if (busyOp) return
    setBusyOp('reward')
    try {
      const r = await fetchJson('/api/rl/reward/stats')
      if (r?.ok !== undefined) setRewardData(r)
    } catch (e) { console.warn('fetchReward:', e) }
    finally { setBusyOp('') }
  }

  async function fetchMeta() {
    if (busyOp) return
    setBusyOp('meta')
    try {
      const r = await fetchJson('/api/rl/meta/status')
      if (r?.ok !== undefined) setMetaData(r)
    } catch (e) { console.warn('fetchMeta:', e) }
    finally { setBusyOp('') }
  }

  async function fetchMetaTune() {
    if (busyOp) return
    setBusyOp('metaTune')
    try {
      const r = await fetchJson('/api/rl/meta/tune', { method: 'POST' })
      if (r) setMetaData((prev) => prev ? { ...prev, _lastTune: r } : r)
    } catch (e) { console.warn('fetchMetaTune:', e) }
    finally { setBusyOp('') }
  }

  // ─── Round 8 fetch functions ──────────────────────
  async function fetchMultiObjective() {
    if (busyOp) return
    setBusyOp('mo')
    try {
      const r = await fetchJson('/api/rl/multi-objective/stats')
      if (r?.ok) setMoData(r)
    } catch (e) { console.warn('fetchMultiObjective:', e) }
    finally { setBusyOp('') }
  }

  async function fetchTradeOff() {
    if (busyOp) return
    setBusyOp('tradeoff')
    try {
      const r = await fetchJson('/api/rl/multi-objective/trade-off')
      if (r?.ok) setTradeOffData(r)
    } catch (e) { console.warn('fetchTradeOff:', e) }
    finally { setBusyOp('') }
  }

  async function fetchTransfer() {
    if (busyOp) return
    setBusyOp('transfer')
    try {
      const r = await fetchJson('/api/rl/transfer/stats')
      if (r?.ok) setTransferData(r)
    } catch (e) { console.warn('fetchTransfer:', e) }
    finally { setBusyOp('') }
  }

  async function fetchTransferSuggest(domain = 'coding') {
    if (busyOp) return
    setBusyOp('transferSuggest')
    try {
      const r = await fetchJson(`/api/rl/transfer/suggest?target_domain=${encodeURIComponent(domain)}`)
      if (r?.ok !== undefined) setTransferSuggestion(r)
    } catch (e) { console.warn('fetchTransferSuggest:', e) }
    finally { setBusyOp('') }
  }

  async function applyTransfer(domain = 'coding') {
    if (busyOp) return
    if (!window.confirm(`"${domain}" への転移を適用しますか？`)) return
    setBusyOp('transferApply')
    try {
      const r = await fetchJson('/api/rl/transfer/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(domain),
      })
      if (r) setTransferSuggestion(r)
    } catch (e) { console.warn('applyTransfer:', e) }
    finally { setBusyOp('') }
  }

  async function fetchEnsemble() {
    if (busyOp) return
    setBusyOp('ensemble')
    try {
      const r = await fetchJson('/api/rl/ensemble/stats')
      if (r?.ok) setEnsembleData(r)
    } catch (e) { console.warn('fetchEnsemble:', e) }
    finally { setBusyOp('') }
  }

  async function fetchEnsembleDecide(method = '') {
    if (busyOp) return
    setBusyOp('ensembleDecide')
    try {
      const url = `/api/rl/ensemble/decide?success_rate=0.5&avg_score=0.5${method ? `&method=${method}` : ''}`
      const r = await fetchJson(url)
      if (r?.ok !== undefined) setEnsembleDecision(r)
    } catch (e) { console.warn('fetchEnsembleDecide:', e) }
    finally { setBusyOp('') }
  }

  async function fetchDiversity() {
    if (busyOp) return
    setBusyOp('diversity')
    try {
      const r = await fetchJson('/api/rl/ensemble/diversity')
      if (r?.ok) setDiversityData(r)
    } catch (e) { console.warn('fetchDiversity:', e) }
    finally { setBusyOp('') }
  }

  const display = liveData || rl

  return (
    <div>
      <div className="panelTitle">強化学習 (RLAnything) <span className="small">3要素同時最適化</span></div>

      {!enabled ? (
        <div className="err">RLAnything が無効または未初期化（start_rl_anything.ps1 で有効化）</div>
      ) : null}

      <div className="grid">
        <Box title="方策 (Policy)">
          <div className="kv"><span>タスク完了数</span><span className="mono">{obs.total ?? 0}</span></div>
          <div className="kv"><span>成功率</span><span className={Number(obs.success_rate || 0) >= 0.7 ? 'ok' : Number(obs.success_rate || 0) >= 0.4 ? 'caution' : 'danger'}>{((obs.success_rate ?? 0) * 100).toFixed(1)}%</span></div>
          <div className="kv"><span>進行中タスク</span><span className="mono">{obs.active_tasks ?? 0}</span></div>
          <div className="kv"><span>平均アクション/タスク</span><span className="mono">{obs.avg_actions_per_task ?? '—'}</span></div>
        </Box>

        <Box title="報酬 (Reward)">
          <div className="kv"><span>サイクル数</span><span className="mono">{rl?.cycle_count ?? 0}</span></div>
          <div className="kv"><span>統合回数</span><span className="mono">{fb.integration_runs ?? 0}</span></div>
          <div className="kv"><span>一貫性更新</span><span className="mono">{fb.consistency_updates ?? 0}</span></div>
          <div className="kv"><span>評価回数</span><span className="mono">{fb.evaluation_runs ?? 0}</span></div>
        </Box>

        <Box title="環境 (Environment)">
          <div className="kv"><span>難易度</span><span className={`mono ${difficultyColor(rl?.current_difficulty)}`}>{String(rl?.current_difficulty || '—').toUpperCase()}</span></div>
          <div className="kv"><span>学習スキル数</span><span className="mono">{evo.skills_count ?? 0}</span></div>
          <div className="kv"><span>難易度変更回数</span><span className="mono">{evo.difficulty_changes ?? 0}</span></div>
          <div className="kv"><span>MEMORY.md更新</span><span className="mono">{evo.memory_updates ?? 0}</span></div>
        </Box>

        <Box title="スコアリング基準（自動更新）">
          {Object.keys(criteria).length > 0 ? (
            Object.entries(criteria).map(([k, v]) => (
              <div key={k} className="kv">
                <span>{k}</span>
                <span className="mono">{typeof v === 'number' ? (v * 100).toFixed(0) + '%' : String(v)}</span>
              </div>
            ))
          ) : (
            <div className="small">基準データなし</div>
          )}
        </Box>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">SKILLS</span>
          <span>学習済みスキル</span>
          <span className="small">{skills.length}件</span>
        </div>
        {skills.length === 0 ? (
          <div className="small">まだスキルが抽出されていません（タスクを3回以上完了すると自動抽出）</div>
        ) : (
          <div className="table">
            <div className="tr th colsRlSkills">
              <div>NAME</div><div>DESCRIPTION</div><div>SUCCESS</div><div>SAMPLES</div>
            </div>
            {skills.map((s) => (
              <div key={s.skill_id || s.name} className="tr colsRlSkills">
                <div className="mono">{s.name}</div>
                <div className="small">{s.description}</div>
                <div className={Number(s.success_rate || 0) >= 0.7 ? 'ok' : 'caution'}>{((s.success_rate ?? 0) * 100).toFixed(0)}%</div>
                <div className="mono">{s.sample_count ?? '—'}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">CONTROL</span>
          <span>タスク手動操作</span>
          <span className="small">API: /api/rl/task/*</span>
        </div>
        <div className="boxBody">
          <div className="kv"><span>TASK ID</span>
            <span><input className="input inputFlush" value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="task-001 (空なら自動生成)" aria-label="タスクID" /></span>
          </div>
          <div className="kv"><span>DESCRIPTION</span>
            <span><input className="input inputFlush" value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)} placeholder="タスクの説明" aria-label="タスクの説明" /></span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runTaskBegin} disabled={!!busyOp}>{busyOp === 'begin' ? '開始中…' : '▶ タスク開始'}</button>
            <button className="link" onClick={() => runTaskEnd('success')} disabled={!!busyOp || !taskId.trim()}>{busyOp === 'end' ? '…' : '✅ 成功終了'}</button>
            <button className="link" onClick={() => runTaskEnd('partial')} disabled={!!busyOp || !taskId.trim()}>⚠ 部分終了</button>
            <button className="link" onClick={() => runTaskEnd('failure')} disabled={!!busyOp || !taskId.trim()}>❌ 失敗終了</button>
          </div>
          {taskOut ? <OutputBlock text={taskOut} onClear={() => setTaskOut('')} /> : <div className="small">結果はここに出る（自動スコアリング + 進化サイクル結果）</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">LIVE</span>
          <span>リアルタイムダッシュボード</span>
          <span className="small">/api/rl/dashboard</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchLiveDashboard} disabled={!!busyOp}>{busyOp === 'live' ? '取得中…' : '最新取得'}</button>
          </div>
          {liveErr ? <div className="small danger">{liveErr}</div> : null}
          {liveData ? <OutputBlock text={JSON.stringify(liveData, null, 2)} onClear={() => setLiveData(null)} /> : <div className="small">ボタンを押すと /api/rl/dashboard の生データを表示</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">HISTORY</span>
          <span>サイクル履歴</span>
          <span className="small">/api/rl/history</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchHistory} disabled={!!busyOp}>{busyOp === 'history' ? '取得中…' : '📊 履歴取得'}</button>
            <button className="link" onClick={runCleanup} disabled={!!busyOp}>🧹 Stale一掃</button>
            <button className="link" onClick={runConfigReload} disabled={!!busyOp}>🔄 Config再読込</button>
          </div>
          {historyErr ? <div className="small danger">{historyErr}</div> : null}
          {historyData && historyData.length > 0 ? (
            <div>
              <div className="table">
                <div className="tr th colsRlHistory">
                  <div>#</div><div>TASK</div><div>OUTCOME</div><div>SCORE</div><div>DIFF</div><div>SKILLS</div><div>RATE</div>
                </div>
                {historyData.slice().reverse().map((h, i) => (
                  <div key={i} className="tr colsRlHistory">
                    <div className="mono">{h.cycle ?? '—'}</div>
                    <div className="small" title={h.task_id}>{(h.task_id || '?').slice(0, 24)}</div>
                    <div className={h.outcome === 'success' ? 'ok' : h.outcome === 'failure' ? 'danger' : 'caution'}>{h.outcome}</div>
                    <div className="mono">{h.score != null ? Number(h.score).toFixed(2) : '—'}</div>
                    <div className="mono">{h.difficulty ?? '—'}</div>
                    <div className="mono">{h.skills_total ?? '—'}</div>
                    <div className="mono">{h.success_rate != null ? (Number(h.success_rate) * 100).toFixed(0) + '%' : '—'}</div>
                  </div>
                ))}
              </div>
              <div className="small mt4">直近 {historyData.length} サイクル（新しい順）</div>
            </div>
          ) : historyData ? (
            <div className="small">履歴なし（タスクを完了するとここに蓄積）</div>
          ) : (
            <div className="small">ボタンを押すと直近のサイクルが表形式で表示</div>
          )}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">ANALYTICS</span>
          <span>トレンド分析</span>
          <span className="small">/api/rl/analytics</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchAnalytics} disabled={!!busyOp}>{busyOp === 'analytics' ? '分析中…' : '📈 トレンド分析'}</button>
            <button className="link" onClick={() => toggleScheduler('start')} disabled={!!busyOp}>⏱ Scheduler開始</button>
            <button className="link" onClick={() => toggleScheduler('stop')} disabled={!!busyOp}>⏹ Scheduler停止</button>
          </div>
          {analyticsErr ? <div className="small danger">{analyticsErr}</div> : null}
          {analyticsData ? (
            <div>
              <div className="grid mt8">
                <Box title="Rolling 成功率">
                  {Object.entries(analyticsData.rolling_success_rate || {}).map(([k, v]) => (
                    <div key={k} className="kv"><span>{k}</span><span className={v >= 0.7 ? 'ok' : v >= 0.4 ? 'caution' : 'danger'}>{(v * 100).toFixed(1)}%</span></div>
                  ))}
                  {Object.keys(analyticsData.rolling_success_rate || {}).length === 0 && <div className="small">データ不足</div>}
                </Box>
                <Box title="Rolling 平均スコア">
                  {Object.entries(analyticsData.rolling_avg_score || {}).map(([k, v]) => (
                    <div key={k} className="kv"><span>{k}</span><span className="mono">{Number(v).toFixed(3)}</span></div>
                  ))}
                  {Object.keys(analyticsData.rolling_avg_score || {}).length === 0 && <div className="small">データ不足</div>}
                </Box>
                <Box title="Outcome 分布">
                  {Object.entries(analyticsData.outcome_distribution || {}).map(([k, v]) => (
                    <div key={k} className="kv"><span className={k === 'success' ? 'ok' : k === 'failure' ? 'danger' : 'caution'}>{k}</span><span className="mono">{v}</span></div>
                  ))}
                </Box>
                <Box title="サマリ">
                  <div className="kv"><span>総サイクル</span><span className="mono">{analyticsData.total_cycles ?? 0}</span></div>
                  <div className="kv"><span>スコア中央値</span><span className="mono">{analyticsData.score_series?.length > 0 ? Number(analyticsData.score_series.slice().sort((a,b) => a - b)[Math.floor(analyticsData.score_series.length / 2)]).toFixed(3) : '—'}</span></div>
                </Box>
              </div>
              {analyticsData.score_series && analyticsData.score_series.length >= 2 ? (
                <div className="mt8">
                  <div className="small mb4">スコア推移（SVGスパークライン）</div>
                  <Sparkline values={analyticsData.score_series} width={400} height={48} color="var(--ok)" />
                </div>
              ) : null}
              {analyticsData.skill_growth && analyticsData.skill_growth.length >= 2 ? (
                <div className="mt8">
                  <div className="small mb4">スキル成長</div>
                  <Sparkline values={analyticsData.skill_growth.map(g => g.skills_total || 0)} width={400} height={36} color="var(--caution)" />
                </div>
              ) : null}
            </div>
          ) : (
            <div className="small">ボタンを押すとローリング統計・推移チャートを表示</div>
          )}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">REPLAY BUFFER</span>
          <span>経験リプレイ</span>
          <span className="small">/api/rl/replay</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchReplayStats} disabled={!!busyOp}>{busyOp === 'replay' ? '取得中…' : '📦 バッファ統計'}</button>
            <button className="link" onClick={() => fetchReplaySamples(false)} disabled={!!busyOp}>🎲 ランダムサンプル</button>
            <button className="link" onClick={() => fetchReplaySamples(true)} disabled={!!busyOp}>⚡ 優先サンプル</button>
          </div>
          {replayStats ? (
            <div className="grid mt8">
              <Box title="バッファ状態">
                <div className="kv"><span>サイズ</span><span className="mono">{replayStats.size} / {replayStats.max_size}</span></div>
                <div className="kv"><span>累計Push</span><span className="mono">{replayStats.total_pushed}</span></div>
                <div className="kv"><span>平均スコア</span><span className="mono">{Number(replayStats.avg_score || 0).toFixed(3)}</span></div>
                <div className="kv"><span>平均優先度</span><span className="mono">{Number(replayStats.avg_priority || 0).toFixed(3)}</span></div>
              </Box>
              {replayStats.outcome_distribution ? (
                <Box title="Outcome分布">
                  {Object.entries(replayStats.outcome_distribution).map(([k, v]) => (
                    <div key={k} className="kv"><span className={k === 'success' ? 'ok' : k === 'failure' ? 'danger' : 'caution'}>{k}</span><span className="mono">{v}</span></div>
                  ))}
                </Box>
              ) : null}
            </div>
          ) : <div className="small">ボタンを押すと Replay Buffer 統計を表示</div>}
          {replaySamples && replaySamples.length > 0 ? (
            <div className="mt8 scrollBox">
              <table className="simple-table tableCompact">
                <thead><tr><th>task</th><th>outcome</th><th>score</th><th>diff</th><th>prio</th></tr></thead>
                <tbody>
                  {replaySamples.map((s, i) => (
                    <tr key={i}>
                      <td className="mono">{String(s.task_id).slice(0, 16)}</td>
                      <td className={s.outcome === 'success' ? 'ok' : s.outcome === 'failure' ? 'danger' : 'caution'}>{s.outcome}</td>
                      <td className="mono">{Number(s.score).toFixed(3)}</td>
                      <td>{s.difficulty}</td>
                      <td className="mono">{Number(s.priority).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">A/B EXPERIMENTS</span>
          <span>実験トラッカー</span>
          <span className="small">/api/rl/experiments</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchExperiments} disabled={!!busyOp}>{busyOp === 'experiments' ? '取得中…' : '🧪 実験一覧'}</button>
          </div>
          {experimentsData ? (
            <div className="mt8">
              <div className="kv"><span>総実験数</span><span className="mono">{experimentsData.total_experiments}</span></div>
              <div className="kv"><span>アクティブ</span><span className="mono">{experimentsData.active_experiments}</span></div>
              <div className="kv"><span>総結果数</span><span className="mono">{experimentsData.total_results}</span></div>
              {experimentsData.experiments && experimentsData.experiments.length > 0 ? (
                <table className="simple-table tableCompact mt8">
                  <thead><tr><th>ID</th><th>名前</th><th>N</th><th>成功率</th><th>平均スコア</th><th>状態</th></tr></thead>
                  <tbody>
                    {experimentsData.experiments.map((e, i) => (
                      <tr key={i}>
                        <td className="mono">{e.exp_id}</td>
                        <td>{e.name}</td>
                        <td className="mono">{e.sample_count}</td>
                        <td className="mono">{(e.success_rate * 100).toFixed(1)}%</td>
                        <td className="mono">{Number(e.avg_score).toFixed(3)}</td>
                        <td className={e.active ? 'ok' : 'small'}>{e.active ? 'active' : 'concluded'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="small">実験なし</div>}
            </div>
          ) : <div className="small">ボタンを押すと A/B 実験一覧を表示</div>}
          {expCompare && expCompare.experiments && expCompare.experiments.length > 0 ? (
            <div className="mt8">
              <div className="small mb4">横比較レポート</div>
              {expCompare.experiments.map((e, i) => (
                <div key={i} className="kv kvBorder" style={{ borderLeft: `3px solid ${e.status === 'ready' ? 'var(--ok)' : 'var(--caution)'}` }}>
                  <span>{e.name} ({e.exp_id})</span>
                  <span className="mono">{e.status === 'ready' ? `${(e.success_rate * 100).toFixed(1)}% / ${Number(e.avg_score).toFixed(3)} ±${Number(e.score_stddev || 0).toFixed(3)}` : 'データ不足'}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {/* ───────── AUTO-CURRICULUM (Round 6) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">AUTO-CURRICULUM</span>
          <span>適応的難易度調整</span>
          <span className="small">/api/rl/curriculum</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchCurriculum} disabled={!!busyOp}>{busyOp === 'curriculum' ? '分析中…' : '📊 推薦を取得'}</button>
            <button className="link" onClick={applyCurriculum} disabled={!!busyOp}>{busyOp === 'curriculum_apply' ? '適用中…' : '⚡ 推薦を即適用'}</button>
          </div>
          {curriculumData ? (
            <div className="mt8">
              <div className="kv"><span>現在の難易度</span><span className="mono">{curriculumData.current}</span></div>
              <div className="kv"><span>推薦</span><span className={`mono ${curriculumData.changed ? 'ok' : ''}`}>{curriculumData.recommended}</span></div>
              <div className="kv"><span>変更</span><span className={curriculumData.changed ? 'ok' : 'small'}>{curriculumData.changed ? '✅ YES' : 'ステイ'}</span></div>
              <div className="kv"><span>確信度</span><span className="mono">{(curriculumData.confidence * 100).toFixed(1)}%</span></div>
              {curriculumData.applied !== undefined && (
                <div className="kv"><span>適用</span><span className={curriculumData.applied ? 'ok' : 'small'}>{curriculumData.applied ? '✅ 適用済み' : '未適用'}</span></div>
              )}
              <div className="small mt4">{curriculumData.reasoning}</div>
              {curriculumData.signals ? (
                <div className="mt4">
                  <div className="small mb4">シグナル</div>
                  <div className="statsGrid">
                    {Object.entries(curriculumData.signals).map(([k, v]) => (
                      <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{typeof v === 'number' ? Number(v).toFixed(4) : String(v)}</span></div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : <div className="small">ボタンを押すとカリキュラム推薦を表示</div>}
        </div>
      </div>

      {/* ───────── REPLAY RE-EVALUATION (Round 6) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">REPLAY RE-EVALUATION</span>
          <span>過去の経験を再評価</span>
          <span className="small">/api/rl/replay/evaluate</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchReplayEval} disabled={!!busyOp}>{busyOp === 'replay_eval' ? '再評価中…' : '🔄 再評価を実行'}</button>
          </div>
          {replayEvalData && replayEvalData.ok ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>評価数</span><span className="mono">{replayEvalData.total_evaluated}</span></div>
                <div className="kv"><span>平均ドリフト</span><span className={`mono ${replayEvalData.avg_drift > 0.01 ? 'ok' : replayEvalData.avg_drift < -0.01 ? 'err' : ''}`}>{replayEvalData.avg_drift > 0 ? '+' : ''}{Number(replayEvalData.avg_drift).toFixed(4)}</span></div>
                <div className="kv"><span>スコア上昇</span><span className="mono ok">{replayEvalData.positive_drift_count}</span></div>
                <div className="kv"><span>スコア低下</span><span className="mono err">{replayEvalData.negative_drift_count}</span></div>
              </div>
              {replayEvalData.drift_by_outcome ? (
                <div className="mt4">
                  <div className="small mb4">Outcome別ドリフト</div>
                  {Object.entries(replayEvalData.drift_by_outcome).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className={`mono ${v > 0.01 ? 'ok' : v < -0.01 ? 'err' : ''}`}>{v > 0 ? '+' : ''}{Number(v).toFixed(4)}</span></div>
                  ))}
                </div>
              ) : null}
              {replayEvalData.insights && replayEvalData.insights.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">💡 インサイト</div>
                  {replayEvalData.insights.map((ins, i) => (
                    <div key={i} className="small" style={{ paddingLeft: '0.5rem', borderLeft: '2px solid var(--accent)', marginBottom: '2px' }}>{ins}</div>
                  ))}
                </div>
              ) : null}
              {replayEvalData.results && replayEvalData.results.length > 0 ? (
                <details className="mt4">
                  <summary className="small">詳細結果 ({replayEvalData.results.length}件)</summary>
                  <table className="simple-table tableCompact mt4">
                    <thead><tr><th>Task</th><th>旧スコア</th><th>新スコア</th><th>ドリフト</th><th>理由</th></tr></thead>
                    <tbody>
                      {replayEvalData.results.slice(0, 20).map((r, i) => (
                        <tr key={i}>
                          <td className="mono">{r.task_id?.substring(0, 16)}</td>
                          <td className="mono">{Number(r.original_score).toFixed(3)}</td>
                          <td className="mono">{Number(r.new_score).toFixed(3)}</td>
                          <td className={`mono ${r.drift > 0.01 ? 'ok' : r.drift < -0.01 ? 'err' : ''}`}>{r.drift > 0 ? '+' : ''}{Number(r.drift).toFixed(3)}</td>
                          <td className="small">{r.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              ) : null}
            </div>
          ) : replayEvalData && !replayEvalData.ok ? (
            <div className="err">{replayEvalData.error || 'エラー'}</div>
          ) : <div className="small">ボタンを押すとリプレイバッファの経験を再評価</div>}
        </div>
      </div>

      {/* ───────── ANOMALY ALERTS (Round 6) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">ANOMALY DETECTION</span>
          <span>異常検知 & アラート</span>
          <span className="small">/api/rl/alerts</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchAlerts} disabled={!!busyOp}>{busyOp === 'alerts' ? 'チェック中…' : '🚨 異常チェック'}</button>
          </div>
          {alertsData && alertsData.ok ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>総アラート数</span><span className="mono">{alertsData.total_alerts}</span></div>
                <div className="kv"><span>新規アラート</span><span className={`mono ${alertsData.count > 0 ? 'err' : 'ok'}`}>{alertsData.count}</span></div>
              </div>
              {alertsData.by_severity ? (
                <div className="mt4">
                  <div className="small mb4">重要度別</div>
                  {Object.entries(alertsData.by_severity).map(([k, v]) => (
                    <div key={k} className="kv"><span className={`small ${k === 'critical' ? 'err' : k === 'warning' ? 'caution' : ''}`}>{k}</span><span className="mono">{v}</span></div>
                  ))}
                </div>
              ) : null}
              {alertsData.recent && alertsData.recent.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">直近アラート</div>
                  {alertsData.recent.slice(-8).reverse().map((a, i) => (
                    <div key={i} className="kv kvBorder" style={{ borderLeft: `3px solid ${a.severity === 'critical' ? 'var(--danger)' : a.severity === 'warning' ? 'var(--caution)' : 'var(--accent)'}` }}>
                      <span className="small">[{a.alert_type}] {a.message}</span>
                      <span className="mono small">{a.severity}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="small mt4">アラートなし — 正常 ✅</div>}
            </div>
          ) : alertsData && !alertsData.ok ? (
            <div className="err">{alertsData.error || 'エラー'}</div>
          ) : <div className="small">ボタンを押すとパフォーマンス異常をチェック</div>}
        </div>
      </div>

      {/* ───────── POLICY GRADIENT (Round 7) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">POLICY GRADIENT</span>
          <span>方策勾配推定 (REINFORCE)</span>
          <span className="small">/api/rl/policy</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchPolicy} disabled={!!busyOp}>{busyOp === 'policy' ? '取得中…' : '📊 ポリシー取得'}</button>
            <button className="link" onClick={fetchPolicyUpdate} disabled={!!busyOp}>{busyOp === 'policyUpdate' ? '更新中…' : '⚡ 手動更新'}</button>
          </div>
          {policyData && policyData.ok ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>学習率</span><span className="mono">{policyData.learning_rate}</span></div>
                <div className="kv"><span>温度</span><span className="mono">{policyData.temperature}</span></div>
                <div className="kv"><span>ベースライン</span><span className="mono">{typeof policyData.baseline === 'number' ? policyData.baseline.toFixed(4) : '—'}</span></div>
                <div className="kv"><span>更新回数</span><span className="mono">{policyData.update_count}</span></div>
                <div className="kv"><span>エントロピ係数</span><span className="mono">{policyData.entropy_coeff}</span></div>
              </div>
              {policyData.stats ? (
                <div className="mt4">
                  <div className="small mb4">統計</div>
                  <div className="statsGrid">
                    <div className="kv"><span>軌跡数</span><span className="mono">{policyData.stats.trajectory_count}</span></div>
                    {policyData.stats.recent_actions ? Object.entries(policyData.stats.recent_actions).map(([k, v]) => (
                      <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{v}</span></div>
                    )) : null}
                  </div>
                </div>
              ) : null}
              {policyData.theta ? (
                <details className="mt4">
                  <summary className="link">θ パラメータ</summary>
                  <pre className="mono small">{JSON.stringify(policyData.theta, null, 2)}</pre>
                </details>
              ) : null}
            </div>
          ) : policyData && !policyData.ok ? (
            <div className="err">{policyData.error || 'エラー'}</div>
          ) : <div className="small">方策パラメータと REINFORCE 更新の状態</div>}
        </div>
      </div>

      {/* ───────── REWARD SHAPER (Round 7) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">REWARD SHAPER</span>
          <span>報酬シェイピング (Potential-Based)</span>
          <span className="small">/api/rl/reward</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchReward} disabled={!!busyOp}>{busyOp === 'reward' ? '取得中…' : '🎯 統計取得'}</button>
          </div>
          {rewardData && rewardData.ok ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>累計訪問数</span><span className="mono">{rewardData.total_visits}</span></div>
                <div className="kv"><span>スコア履歴数</span><span className="mono">{rewardData.score_history_len}</span></div>
                <div className="kv"><span>直近平均スコア</span><span className="mono">{typeof rewardData.recent_avg_score === 'number' ? rewardData.recent_avg_score.toFixed(4) : '—'}</span></div>
                <div className="kv"><span>現在ポテンシャル</span><span className="mono">{typeof rewardData.current_potential === 'number' ? rewardData.current_potential.toFixed(4) : '—'}</span></div>
              </div>
              {rewardData.visit_distribution ? (
                <div className="mt4">
                  <div className="small mb4">訪問分布</div>
                  {Object.entries(rewardData.visit_distribution).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{v}</span></div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : rewardData && !rewardData.ok ? (
            <div className="err">{rewardData.error || 'エラー'}</div>
          ) : <div className="small">PBRS + 好奇心ボーナス + 一貫性ボーナスの統計</div>}
        </div>
      </div>

      {/* ───────── META-CONTROLLER (Round 7) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">META-CONTROLLER</span>
          <span>自律ハイパーパラメータ調整</span>
          <span className="small">/api/rl/meta</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchMeta} disabled={!!busyOp}>{busyOp === 'meta' ? '取得中…' : '🧠 状態取得'}</button>
            <button className="link" onClick={fetchMetaTune} disabled={!!busyOp}>{busyOp === 'metaTune' ? '調整中…' : '🔧 手動チューニング'}</button>
          </div>
          {metaData && metaData.ok ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>総調整回数</span><span className="mono">{metaData.total_adjustments}</span></div>
                <div className="kv"><span>メタ履歴数</span><span className="mono">{metaData.meta_history_len}</span></div>
              </div>
              {metaData.latest_signals && Object.keys(metaData.latest_signals).length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">最新メタシグナル</div>
                  {Object.entries(metaData.latest_signals).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className={`mono ${k === 'stability' && v < 0.4 ? 'err' : k === 'convergence' && v < -0.05 ? 'err' : ''}`}>{typeof v === 'number' ? v.toFixed(4) : v}</span></div>
                  ))}
                </div>
              ) : null}
              {metaData.health_trend && metaData.health_trend.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">ヘルストレンド</div>
                  <div className="mono small">{metaData.health_trend.map((h) => h.toFixed(2)).join(' → ')}</div>
                </div>
              ) : null}
              {metaData.param_change_counts && Object.keys(metaData.param_change_counts).length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">パラメータ変更回数</div>
                  {Object.entries(metaData.param_change_counts).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{v}</span></div>
                  ))}
                </div>
              ) : null}
              {metaData.recent_adjustments && metaData.recent_adjustments.length > 0 ? (
                <details className="mt4">
                  <summary className="link">直近の調整ログ</summary>
                  {metaData.recent_adjustments.slice(-5).reverse().map((a, i) => (
                    <div key={i} className="kv kvBorder mt4">
                      <span className="small">[{a.param_name}] {a.old_value?.toFixed?.(4)} → {a.new_value?.toFixed?.(4)}</span>
                      <span className="mono small">{a.reason}</span>
                    </div>
                  ))}
                </details>
              ) : null}
            </div>
          ) : metaData && !metaData.ok ? (
            <div className="err">{metaData.error || 'エラー'}</div>
          ) : <div className="small">メタ学習による lr / 温度 / 閾値の自動調整</div>}
        </div>
      </div>

      {/* ───────── MULTI-OBJECTIVE OPTIMIZER (Round 8) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">MULTI-OBJECTIVE</span>
          <span>パレートフロント & トレードオフ</span>
          <span className="small">/api/rl/multi-objective</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchMultiObjective} disabled={!!busyOp}>{busyOp === 'mo' ? '取得中…' : '📊 統計取得'}</button>
            <button className="link" onClick={fetchTradeOff} disabled={!!busyOp}>{busyOp === 'tradeoff' ? '分析中…' : '⚖ トレードオフ'}</button>
          </div>
          {moData ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>総ソリューション数</span><span className="mono">{moData.total_solutions ?? 0}</span></div>
                <div className="kv"><span>パレートサイズ</span><span className="mono ok">{moData.pareto_size ?? 0}</span></div>
              </div>
              {moData.objectives && moData.objectives.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">目的関数</div>
                  {moData.objectives.map((o, i) => (
                    <div key={i} className="kv"><span className="small">{o.name} ({o.direction})</span><span className="mono">w={Number(o.weight).toFixed(2)}</span></div>
                  ))}
                </div>
              ) : null}
              {moData.best_scalarized ? (
                <div className="mt4">
                  <div className="small mb4">ベストスカラ化</div>
                  <div className="kv"><span>スコア</span><span className="mono ok">{Number(moData.best_scalarized.scalarized || 0).toFixed(4)}</span></div>
                  <div className="kv"><span>サイクル</span><span className="mono">{moData.best_scalarized.cycle ?? '—'}</span></div>
                </div>
              ) : null}
              {moData.recommended_weights ? (
                <div className="mt4">
                  <div className="small mb4">推奨ウェイト</div>
                  {Object.entries(moData.recommended_weights).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{Number(v).toFixed(3)}</span></div>
                  ))}
                </div>
              ) : null}
              {moData.pareto_front && moData.pareto_front.length > 0 ? (
                <details className="mt4">
                  <summary className="link">パレートフロント ({moData.pareto_front.length}件)</summary>
                  <table className="simple-table tableCompact mt4">
                    <thead><tr><th>Cycle</th><th>Score</th><th>Scalarized</th></tr></thead>
                    <tbody>
                      {moData.pareto_front.slice(0, 20).map((p, i) => (
                        <tr key={i}>
                          <td className="mono">{p.cycle}</td>
                          <td className="mono">{p.values?.score != null ? Number(p.values.score).toFixed(3) : '—'}</td>
                          <td className="mono ok">{Number(p.scalarized).toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              ) : null}
            </div>
          ) : <div className="small">パレートフロントと多目的最適化の統計</div>}
          {tradeOffData ? (
            <div className="mt8">
              <div className="small mb4">トレードオフ分析</div>
              {tradeOffData.trends && Object.keys(tradeOffData.trends).length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">トレンド</div>
                  {Object.entries(tradeOffData.trends).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className={`mono ${v === 'improving' ? 'ok' : v === 'worsening' ? 'err' : ''}`}>{v}</span></div>
                  ))}
                </div>
              ) : null}
              {tradeOffData.conflicts && tradeOffData.conflicts.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">コンフリクト（負の相関）</div>
                  {tradeOffData.conflicts.map((c, i) => (
                    <div key={i} className="kv kvBorder" style={{ borderLeft: '3px solid var(--danger)' }}>
                      <span className="small">{c[0]} vs {c[1]}</span>
                      <span className="mono err">{Number(c[2]).toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="small">コンフリクトなし ✅</div>}
            </div>
          ) : null}
        </div>
      </div>

      {/* ───────── TRANSFER LEARNING (Round 8) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">TRANSFER LEARNING</span>
          <span>ドメイン間知識転移</span>
          <span className="small">/api/rl/transfer</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchTransfer} disabled={!!busyOp}>{busyOp === 'transfer' ? '取得中…' : '📊 統計取得'}</button>
            <button className="link" onClick={() => fetchTransferSuggest('coding')} disabled={!!busyOp}>{busyOp === 'transferSuggest' ? '分析中…' : '💡 転移提案'}</button>
            <button className="link" onClick={() => applyTransfer('coding')} disabled={!!busyOp}>{busyOp === 'transferApply' ? '適用中…' : '⚡ 転移適用'}</button>
          </div>
          {transferData ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>ドメイン数</span><span className="mono">{transferData.domain_count ?? 0}</span></div>
                <div className="kv"><span>累計転移</span><span className="mono">{transferData.transfer_count ?? 0}</span></div>
              </div>
              {transferData.domains && typeof transferData.domains === 'object' ? (
                <div className="mt4">
                  <div className="small mb4">ドメイン一覧</div>
                  <table className="simple-table tableCompact">
                    <thead><tr><th>Domain</th><th>Tasks</th><th>Avg Score</th><th>Success</th></tr></thead>
                    <tbody>
                      {Object.entries(transferData.domains).map(([name, d], i) => (
                        <tr key={i}>
                          <td className="mono">{name}</td>
                          <td className="mono">{d.total_tasks}</td>
                          <td className="mono">{Number(d.avg_score || 0).toFixed(3)}</td>
                          <td className={`mono ${d.success_rate >= 0.7 ? 'ok' : d.success_rate >= 0.4 ? 'caution' : 'danger'}`}>{(d.success_rate * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {transferData.similarity_matrix && Object.keys(transferData.similarity_matrix).length > 0 ? (
                <details className="mt4">
                  <summary className="link">類似度行列</summary>
                  <div className="mt4 scrollBox">
                    {Object.entries(transferData.similarity_matrix).map(([src, targets]) => (
                      <div key={src} className="kv">
                        <span className="mono small">{src}</span>
                        <span className="mono small">{Object.entries(targets).map(([t, v]) => `${t}:${Number(v).toFixed(2)}`).join(' ')}</span>
                      </div>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          ) : <div className="small">ドメイン間の知識転移と類似度</div>}
          {transferSuggestion ? (
            <div className="mt8">
              <div className="small mb4">転移結果</div>
              <OutputBlock text={JSON.stringify(transferSuggestion, null, 2)} onClear={() => setTransferSuggestion(null)} />
            </div>
          ) : null}
        </div>
      </div>

      {/* ───────── ENSEMBLE POLICY (Round 8) ───────── */}
      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">ENSEMBLE POLICY</span>
          <span>多方策アンサンブル</span>
          <span className="small">/api/rl/ensemble</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" onClick={fetchEnsemble} disabled={!!busyOp}>{busyOp === 'ensemble' ? '取得中…' : '📊 統計取得'}</button>
            <button className="link" onClick={() => fetchEnsembleDecide('')} disabled={!!busyOp}>{busyOp === 'ensembleDecide' ? '決定中…' : '🎯 意思決定'}</button>
            <button className="link" onClick={fetchDiversity} disabled={!!busyOp}>{busyOp === 'diversity' ? '取得中…' : '🌈 多様性'}</button>
          </div>
          {ensembleData ? (
            <div className="mt8">
              <div className="statsGrid">
                <div className="kv"><span>メンバー数</span><span className="mono">{ensembleData.member_count ?? 0}</span></div>
                <div className="kv"><span>総決定数</span><span className="mono">{ensembleData.total_decisions ?? 0}</span></div>
              </div>
              {ensembleData.members && ensembleData.members.length > 0 ? (
                <div className="mt4">
                  <div className="small mb4">メンバー</div>
                  <table className="simple-table tableCompact">
                    <thead><tr><th>ID</th><th>Avg Reward</th><th>Decisions</th><th>Accuracy</th><th>Temp</th></tr></thead>
                    <tbody>
                      {ensembleData.members.map((m, i) => (
                        <tr key={i}>
                          <td className="mono">{m.member_id}</td>
                          <td className="mono">{Number(m.avg_reward || 0).toFixed(3)}</td>
                          <td className="mono">{m.decision_count}</td>
                          <td className={`mono ${m.accuracy >= 0.7 ? 'ok' : m.accuracy >= 0.4 ? 'caution' : ''}`}>{(m.accuracy * 100).toFixed(0)}%</td>
                          <td className="mono">{Number(m.temperature).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          ) : <div className="small">アンサンブルメンバーの統計と意思決定</div>}
          {ensembleDecision ? (
            <div className="mt8">
              <div className="small mb4">最新のアンサンブル決定</div>
              <div className="statsGrid">
                <div className="kv"><span>行動</span><span className="mono ok">{ensembleDecision.action ?? '—'}</span></div>
                <div className="kv"><span>合意度</span><span className={`mono ${(ensembleDecision.agreement || 0) >= 0.7 ? 'ok' : 'caution'}`}>{((ensembleDecision.agreement || 0) * 100).toFixed(0)}%</span></div>
                <div className="kv"><span>信頼度</span><span className="mono">{((ensembleDecision.confidence || 0) * 100).toFixed(0)}%</span></div>
                <div className="kv"><span>方式</span><span className="mono small">{ensembleDecision.method ?? '—'}</span></div>
              </div>
              {ensembleDecision.probabilities ? (
                <div className="mt4">
                  <div className="small mb4">確率分布</div>
                  {Object.entries(ensembleDecision.probabilities).map(([k, v]) => (
                    <div key={k} className="kv"><span className="small">{k}</span><span className="mono">{(Number(v) * 100).toFixed(1)}%</span></div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {diversityData ? (
            <div className="mt8">
              <div className="small mb4">多様性指標</div>
              <div className="statsGrid">
                <div className="kv"><span>行動エントロピ</span><span className="mono">{Number(diversityData.action_entropy || 0).toFixed(4)}</span></div>
                <div className="kv"><span>パラメータ分散</span><span className="mono">{Number(diversityData.param_variance || 0).toFixed(4)}</span></div>
                {diversityData.agreement_trend && diversityData.agreement_trend.length > 0 ? (
                  <div className="kv"><span>合意トレンド</span><span className="mono small">{diversityData.agreement_trend.slice(-5).map(v => Number(v).toFixed(2)).join(' → ')}</span></div>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="small mt12">
        Princeton RLAnything (Policy×Reward×Environment 同時最適化) — MEMORY.md 自動更新 / スキル自動抽出 / 難易度自動調整
      </div>
    </div>
  )
}
