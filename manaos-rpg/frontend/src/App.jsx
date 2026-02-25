import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchJson, getApiBase } from './api.js'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, color: '#FF6B6B', fontFamily: 'monospace' }}>
          <h2>レンダーエラー</h2>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{String(this.state.error)}</pre>
          <button onClick={() => this.setState({ error: null })} style={{ marginTop: 12, padding: '8px 16px', cursor: 'pointer' }}>再試行</button>
        </div>
      )
    }
    return this.props.children
  }
}

const TITLE_BASE = 'MANAOS // RPG COMMAND'

const FALLBACK_MENU = [
  { id: 'status', label: 'ステータス', icon: '🧍' },
  { id: 'party', label: 'パーティ（サービス）', icon: '🧩' },
  { id: 'bestiary', label: '図鑑（モデル）', icon: '📚' },
  { id: 'skills', label: '魔法（スキル）', icon: '✨' },
  { id: 'quests', label: 'クエスト（タスク）', icon: '🗺' },
  { id: 'logs', label: '戦闘ログ', icon: '📜' },
  { id: 'map', label: 'マップ（デバイス）', icon: '🧭' },
  { id: 'items', label: 'アイテム（生成物）', icon: '🎒' },
  { id: 'rl', label: '強化学習(RL)', icon: '🧠' },
  { id: 'systems', label: 'システム（統合）', icon: '⚙️' }
]

function pad2(n) {
  return String(n).padStart(2, '0')
}

function fmtTs(ts) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
}

function bar(pct) {
  const p = Math.max(0, Math.min(100, Number(pct || 0)))
  const filled = Math.round((p / 100) * 20)
  return `[${'#'.repeat(filled)}${'.'.repeat(20 - filled)}] ${p.toFixed(0)}%`
}

function dangerRank(danger) {
  const d = Number(danger || 0)
  if (d >= 7) return { label: 'DANGER', cls: 'danger' }
  if (d >= 4) return { label: 'CAUTION', cls: 'caution' }
  return { label: 'OK', cls: 'ok' }
}

function fmtAgo(tsMs, _tick) {
  if (!tsMs) return ''
  const sec = Math.floor((Date.now() - tsMs) / 1000)
  if (sec < 5) return 'たった今'
  if (sec < 60) return `${sec}秒前`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}分前`
  return `${Math.floor(min / 60)}時間前`
}

function logTypeCls(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'DOWN' || t === 'ERROR' || t === 'CRITICAL' || t === 'FATAL') return 'danger'
  if (t === 'RECOVERY' || t === 'START' || t === 'UP' || t === 'RESOLVED') return 'ok'
  if (t === 'WARN' || t === 'WARNING' || t === 'CAUTION' || t === 'SLOW') return 'caution'
  return ''
}

function encodeRelPath(relPath) {
  const p = String(relPath || '').replace(/\\/g, '/')
  return p.split('/').map(encodeURIComponent).join('/')
}

function fmtBytes(n) {
  const v = Number(n || 0)
  if (!Number.isFinite(v) || v <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let x = v
  let i = 0
  while (x >= 1024 && i < units.length - 1) {
    x /= 1024
    i++
  }
  return `${x.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

const DIFFICULTY_CLS = { beginner: 'ok', standard: '', advanced: 'caution', expert: 'danger' }
function difficultyColor(d) { return DIFFICULTY_CLS[String(d)] || '' }

/** SVG スパークライン — values 配列をインライン折れ線チャートで描画 */
function Sparkline({ values = [], width = 300, height = 40, color = '#4ade80', strokeWidth = 1.5 }) {
  if (!values || values.length < 2) return null
  const nums = values.map(Number).filter(Number.isFinite)
  if (nums.length < 2) return null
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const range = max - min || 1
  const padY = 2
  const points = nums.map((v, i) => {
    const x = (i / (nums.length - 1)) * width
    const y = height - padY - ((v - min) / range) * (height - padY * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg width={width} height={height} style={{ display: 'block', background: 'rgba(0,0,0,0.15)', borderRadius: 4 }}>
      <polyline fill="none" stroke={color} strokeWidth={strokeWidth} points={points} />
      <circle cx={(nums.length - 1) / (nums.length - 1) * width} cy={height - padY - ((nums[nums.length - 1] - min) / range) * (height - padY * 2)} r="2.5" fill={color} />
    </svg>
  )
}

function RLView({ rl, apiBase }) {
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
    setBusyOp('scheduler')
    try {
      const r = await fetch(`${apiBase}/api/rl/scheduler/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const d = await r.json().catch(() => ({}))
      setTaskOut(`Scheduler ${action}: ${JSON.stringify(d)}`)
    } catch (e) { setTaskOut(`ERR: ${e?.message}`) }
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
            <div className="tr th" style={{ gridTemplateColumns: '2fr 3fr 0.8fr 0.8fr' }}>
              <div>NAME</div><div>DESCRIPTION</div><div>SUCCESS</div><div>SAMPLES</div>
            </div>
            {skills.map((s) => (
              <div key={s.skill_id || s.name} className="tr" style={{ gridTemplateColumns: '2fr 3fr 0.8fr 0.8fr' }}>
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
            <span><input className="input" value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="task-001 (空なら自動生成)" aria-label="タスクID" style={{ marginTop: 0 }} /></span>
          </div>
          <div className="kv"><span>DESCRIPTION</span>
            <span><input className="input" value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)} placeholder="タスクの説明" aria-label="タスクの説明" style={{ marginTop: 0 }} /></span>
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
                <div className="tr th" style={{ gridTemplateColumns: '0.5fr 1.5fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr' }}>
                  <div>#</div><div>TASK</div><div>OUTCOME</div><div>SCORE</div><div>DIFF</div><div>SKILLS</div><div>RATE</div>
                </div>
                {historyData.slice().reverse().map((h, i) => (
                  <div key={i} className="tr" style={{ gridTemplateColumns: '0.5fr 1.5fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr' }}>
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
              <div className="small" style={{ marginTop: 4 }}>直近 {historyData.length} サイクル（新しい順）</div>
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
              <div className="grid" style={{ marginTop: 8 }}>
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
                  <div className="kv"><span>スコア中央値</span><span className="mono">{analyticsData.score_series?.length > 0 ? Number(analyticsData.score_series.sort((a,b) => a - b)[Math.floor(analyticsData.score_series.length / 2)]).toFixed(3) : '—'}</span></div>
                </Box>
              </div>
              {analyticsData.score_series && analyticsData.score_series.length >= 2 ? (
                <div style={{ marginTop: 8 }}>
                  <div className="small" style={{ marginBottom: 4 }}>スコア推移（SVGスパークライン）</div>
                  <Sparkline values={analyticsData.score_series} width={400} height={48} color="var(--ok)" />
                </div>
              ) : null}
              {analyticsData.skill_growth && analyticsData.skill_growth.length >= 2 ? (
                <div style={{ marginTop: 8 }}>
                  <div className="small" style={{ marginBottom: 4 }}>スキル成長</div>
                  <Sparkline values={analyticsData.skill_growth.map(g => g.skills_total || 0)} width={400} height={36} color="var(--caution)" />
                </div>
              ) : null}
            </div>
          ) : (
            <div className="small">ボタンを押すとローリング統計・推移チャートを表示</div>
          )}
        </div>
      </div>

      <div className="small" style={{ marginTop: 12 }}>
        Princeton RLAnything (Policy×Reward×Environment 同時最適化) — MEMORY.md 自動更新 / スキル自動抽出 / 難易度自動調整
      </div>
    </div>
  )
}

const MONITOR_ROUTES = {
  comfyui_queue: { path: '/api/unified/comfyui/queue', requires: '/api/comfyui/queue' },
  comfyui_history: { path: '/api/unified/comfyui/history', requires: '/api/comfyui/history' },
  svi_queue: { path: '/api/unified/svi/queue', requires: '/api/svi/queue' },
  svi_history: { path: '/api/unified/svi/history', requires: '/api/svi/history' },
  ltx2_queue: { path: '/api/unified/ltx2/queue', requires: '/api/ltx2/queue' },
  ltx2_history: { path: '/api/unified/ltx2/history', requires: '/api/ltx2/history' },
  images_recent: { path: '/api/unified/images/recent?limit=30', requires: '/api/images/recent' },
  llm_health: { path: '/api/unified/llm/health', requires: '/api/llm/health' },
  llm_models: { path: '/api/unified/llm/models-enhanced', requires: '/api/llm/models-enhanced' },
  unified_openapi: { path: '/api/unified/openapi' },
  unified_proxy_doctor: { path: '/api/unified/proxy/doctor?limit=200&probe_timeout_s=1.5&max_total_s=8' }
}

export default function App() {
  const [state, setState] = useState(null)
  const [events, setEvents] = useState([])
  const [active, setActive] = useState('status')
  const [err, setErr] = useState('')
  const [actionResult, setActionResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lastRefreshTs, setLastRefreshTs] = useState(null)
  const [tick, setTick] = useState(0)
  const panelRef = useRef(null)
  const refreshingRef = useRef(false)
  const stateRef = useRef(null)
  const apiBase = useMemo(() => getApiBase(), [])

  const refreshSnapshot = useCallback(async function refreshSnapshot() {
    if (refreshingRef.current) return null
    refreshingRef.current = true
    setErr('')
    setLoading(true)
    try {
      const snap = await fetchJson('/api/snapshot')
      setState(snap)
      setLastRefreshTs(Date.now())
      return snap
    } catch (e) {
      setErr(String(e?.message || e))
      return null
    } finally {
      setLoading(false)
      refreshingRef.current = false
    }
  }, [])

  const refreshState = useCallback(async function refreshState() {
    setErr('')
    setLoading(true)
    try {
      const st = await fetchJson('/api/state')
      setState(st)
      setLastRefreshTs(Date.now())
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }, [])

  const [runningAction, setRunningAction] = useState('')

  // Keep stateRef in sync for stable runAction callback
  stateRef.current = state

  const runAction = useCallback(async function runAction(actionId) {
    setErr('')
    setActionResult(null)
    setRunningAction(actionId)
    try {
      const beforeUnifiedRules = Array.isArray(stateRef.current?.unified?.proxy?.rules) ? stateRef.current.unified.proxy.rules.length : null
      const res = await fetch(`${apiBase}/api/actions/${encodeURIComponent(actionId)}/run`, {
        method: 'POST'
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`)
      }
      const snap = await refreshSnapshot()
      const afterUnifiedRules = Array.isArray(snap?.unified?.proxy?.rules) ? snap.unified.proxy.rules.length : null
      setActionResult({
        ...data,
        meta: {
          before_unified_rules: beforeUnifiedRules,
          after_unified_rules: afterUnifiedRules
        }
      })
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setRunningAction('')
    }
  }, [apiBase, refreshSnapshot])

  useEffect(() => {
    refreshSnapshot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-dismiss error after 15 seconds
  useEffect(() => {
    if (!err) return
    const id = setTimeout(() => setErr(''), 15000)
    return () => clearTimeout(id)
  }, [err])

  const refreshEvents = useCallback(() => {
    fetchJson('/api/events?limit=120')
      .then((r) => setEvents(r.events || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(() => {
      refreshSnapshot().then(() => {
        if (active === 'logs') refreshEvents()
      })
    }, 30000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, active])

  useEffect(() => {
    if (active === 'logs') refreshEvents()
    panelRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [active, refreshEvents])

  // Tick every 60s to keep fmtAgo up-to-date
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 60000)
    return () => clearInterval(id)
  }, [])

  // Keyboard shortcuts: 1-9 for tabs, r for refresh
  useEffect(() => {
    function handleKey(e) {
      // Ignore when typing in input/textarea/select
      const tag = e.target?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      const tabIds = ['status', 'party', 'bestiary', 'skills', 'quests', 'logs', 'map', 'items', 'rl', 'systems']
      if (e.key === '0') {
        e.preventDefault()
        setActive(tabIds[9])
        return
      }
      const num = parseInt(e.key, 10)
      if (num >= 1 && num <= 9) {
        e.preventDefault()
        setActive(tabIds[num - 1])
        return
      }
      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        refreshSnapshot()
      }
      if (e.key === 'Escape') {
        setErr('')
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const menu = Array.isArray(state?.menu) ? state.menu : FALLBACK_MENU

  const rank = dangerRank(state?.danger)

  // Fix 5: Dynamic document title with active tab
  const activeLabel = useMemo(() => {
    const m = menu.find((x) => x.id === active)
    return m?.label || active
  }, [menu, active])

  useEffect(() => {
    if (!state) {
      document.title = TITLE_BASE
    } else {
      const d = Number(state?.danger || 0)
      document.title = `[${rank.label} ${d}] ${activeLabel} — ${TITLE_BASE}`
    }
  }, [state, rank.label, activeLabel])

  // Fix 12: Service alive count
  const services = state?.services
  const aliveCount = useMemo(() => {
    const svcs = Array.isArray(services) ? services : []
    return svcs.filter((s) => s.alive).length
  }, [services])
  const totalCount = Array.isArray(services) ? services.length : 0

  return (
    <ErrorBoundary>
    <div className="screen">
      <header className="header">
        <div className="title">MANAOS // RPG COMMAND</div>
        <div className={`badge ${rank.cls}`}>危険度: {rank.label} ({Number(state?.danger || 0)})</div>
        <div className="meta">
          <span>API: {apiBase}</span>
          <span>サービス: {aliveCount}/{totalCount} alive</span>
          <span>更新: {fmtTs(state?.ts)}{lastRefreshTs ? ` (${fmtAgo(lastRefreshTs, tick)})` : ''}</span>
          <span title="1-9,0: タブ切替 / R: 更新 / Esc: エラー閉じる">⌨ ショートカット有</span>
        </div>
        <div className="actions">
          <button onClick={refreshSnapshot} disabled={loading}>更新（/api/snapshot）</button>
          <button onClick={refreshState} disabled={loading}>読込（/api/state）</button>
          <label className="autoRefresh">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            自動更新（30秒）
            {autoRefresh ? <span className="pulse">●</span> : null}
          </label>
        </div>
        {loading ? <div className="loading" role="status" aria-live="polite">更新中…</div> : null}
        {err ? (
          <div className="err" role="alert" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <span>{err}</span>
            <button className="link" onClick={() => setErr('')} style={{ flexShrink: 0 }} aria-label="エラーを閉じる">✕</button>
          </div>
        ) : null}
      </header>

      <main className="main">
        <nav className="menu" aria-label="メインメニュー">
          <div className="menuTitle">コマンド</div>
          {menu.map((m) => (
            <button
              key={m.id}
              className={m.id === active ? 'menuItem active' : 'menuItem'}
              onClick={() => setActive(m.id)}
            >
              <span className="icon">{m.icon}</span>
              <span className="label">{m.label}</span>
            </button>
          ))}
        </nav>

        <section className="panel" ref={panelRef}>
          {!state && !err ? (
            <div className="loading">データを読み込み中…</div>
          ) : null}
          {state && active === 'status' ? (
            <StatusView
              host={state?.host}
              nextActions={state?.next_actions}
              nextActionHints={state?.next_action_hints}
              onRunAction={runAction}
              actionResult={actionResult}
              actionsEnabled={state?.actions_enabled}
              runningAction={runningAction}
            />
          ) : null}
          {state && active === 'party' ? <PartyView services={state?.services} /> : null}
          {state && active === 'bestiary' ? <BestiaryView models={state?.models} /> : null}
          {state ? (
            <div style={{ display: active === 'skills' ? 'block' : 'none' }}>
              <SkillsView
                skills={state?.skills}
                prompts={state?.prompts}
                unifiedIntegrations={state?.unified?.integrations}
                unifiedProxy={state?.unified?.proxy}
                itemsRecent={state?.items?.recent}
                apiBase={apiBase}
                onRunAction={runAction}
                runningAction={runningAction}
              />
            </div>
          ) : null}
          {state && active === 'quests' ? <QuestsView quests={state?.quests} apiBase={apiBase} onRunAction={runAction} actionResult={actionResult} runningAction={runningAction} /> : null}
          {state && active === 'logs' ? <LogsView events={events} onRefresh={refreshEvents} /> : null}
          {state && active === 'map' ? <MapView devices={state?.devices} /> : null}
          {state && active === 'items' ? <ItemsView items={state?.items} apiBase={apiBase} /> : null}
          {state && active === 'rl' ? <RLView rl={state?.rl_anything} apiBase={apiBase} /> : null}
          {state && active === 'systems' ? (
            <SystemsView
              unified={state?.unified}
              onRunAction={runAction}
              actionResult={actionResult}
              actionsEnabled={state?.actions_enabled}
              runningAction={runningAction}
            />
          ) : null}
        </section>
      </main>
    </div>
    </ErrorBoundary>
  )
}

function Box({ title, children, style }) {
  return (
    <div className="box" style={style}>
      <div className="boxTitle">{title}</div>
      <div className="boxBody">{children}</div>
    </div>
  )
}

function OutputBlock({ text, onClear }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }
  return (
    <div style={{ position: 'relative' }}>
      <pre className="output">{text}</pre>
      <div className="outputActions">
        <button className="link" onClick={handleCopy} aria-label="出力をクリップボードにコピー">{copied ? 'コピー済' : 'コピー'}</button>
        {onClear ? <button className="link" onClick={onClear} aria-label="出力をクリア">クリア</button> : null}
      </div>
    </div>
  )
}

function StatusView({ host, nextActions, nextActionHints, onRunAction, actionResult, actionsEnabled, runningAction }) {
  const cpu = host?.cpu?.percent
  const mem = host?.mem?.percent
  const diskFree = host?.disk?.free_gb
  const diskTotal = host?.disk?.total_gb
  const hostname = host?.host?.hostname
  const os = host?.host?.os
  const diskRoot = host?.host?.disk_root

  const nvidia = Array.isArray(host?.gpu?.nvidia) ? host.gpu.nvidia : []
  const apps = Array.isArray(host?.gpu?.apps) ? host.gpu.apps : []

  const hints = Array.isArray(nextActionHints) ? nextActionHints : []
  const actions = Array.isArray(nextActions) ? nextActions : []

  const filteredNextActions = useMemo(() => {
    const suppressRules = []
    if (hints.some((h) => h?.action_id === 'unified_proxy_disable_404')) {
      suppressRules.push(/404自動無効化|台帳掃除|GET 404/)
    }
    if (hints.some((h) => h?.action_id === 'unified_proxy_sync')) {
      suppressRules.push(/allowlist.*同期|同期\/有効化|同期→/)
    }
    if (suppressRules.length === 0) return actions
    return actions.filter((x) => !suppressRules.some((re) => re.test(String(x || ''))))
  }, [hints, actions])

  return (
    <div className="grid">
      <Box title="母艦ステータス">
        <div className="kv"><span>HOST</span><span>{hostname || '—'}</span></div>
        <div className="kv"><span>OS</span><span className="mono">{os || '—'}</span></div>
        <div className="kv"><span>DISK</span><span>{diskRoot || '—'} / free {diskFree ?? '—'}GB / total {diskTotal ?? '—'}GB</span></div>
      </Box>

      <Box title="CPU">
        <div className="mono">{bar(cpu)}</div>
      </Box>

      <Box title="RAM">
        <div className="mono">{bar(mem)}</div>
        <div className="small">{host?.mem?.used_gb ?? '—'}GB / {host?.mem?.total_gb ?? '—'}GB</div>
      </Box>

      <Box title="GPU (NVIDIA)">
        {nvidia.length === 0 ? (
          <div className="small">nvidia-smi 未検出 / 取得不可</div>
        ) : (
          nvidia.map((g, i) => (
            <div key={i} className="gpuRow">
              <div className="mono">{g.name}</div>
              {typeof g.utilization_gpu === 'number' ? (
                <div className="mono gpuDetail">UTIL {bar(g.utilization_gpu)}</div>
              ) : (
                <div className="small gpuDetail">UTIL —</div>
              )}
              {typeof g.mem_used_mb === 'number' && typeof g.mem_total_mb === 'number' && g.mem_total_mb > 0 ? (
                <div className="mono gpuDetail">VRAM {bar((g.mem_used_mb / g.mem_total_mb) * 100)} ({g.mem_used_mb}MB / {g.mem_total_mb}MB)</div>
              ) : (
                <div className="small gpuDetail">VRAM {g.mem_used_mb ?? '—'}MB / {g.mem_total_mb ?? '—'}MB</div>
              )}
              <div className="small gpuDetail">
                TEMP {g.temperature_c ?? '—'}°C
                {typeof g.power_draw_w === 'number' ? ` / PWR ${g.power_draw_w}W` : ''}
              </div>
            </div>
          ))
        )}
      </Box>

      <Box title="GPUプロセス（VRAM犯人）">
        {apps.length === 0 ? (
          <div className="small">取得なし（nvidia-smi の query-apps が空 / 権限 / 対象プロセスなし）</div>
        ) : (
          <div className="offenders">
            {apps.slice(0, 12).map((a, i) => (
              <div key={i} className="offenderRow">
                <span className="mono">pid={a.pid ?? '—'}</span>
                <span className="mono">{a.used_gpu_memory_mb ?? '—'}MB</span>
                <span className="small">{a.process_name ?? '—'}</span>
              </div>
            ))}
          </div>
        )}
      </Box>

      <Box title="NETWORK">
        <div className="kv"><span>TX</span><span>{fmtBytes(host?.net?.bytes_sent)}</span></div>
        <div className="kv"><span>RX</span><span>{fmtBytes(host?.net?.bytes_recv)}</span></div>
      </Box>

      <Box title="次の一手" style={{ gridColumn: '1 / -1' }}>
        {hints.length > 0 ? (
          <div>
            {hints.map((h, i) => (
              <div key={i} className="hintRow">
                <div className="small">- {h?.label || '—'}</div>
                {h?.action_id ? (
                  <button className="link" disabled={actionsEnabled === false || !!runningAction} onClick={() => onRunAction?.(h.action_id)}>
                    {runningAction === h.action_id ? '実行中…' : '実行'}
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {actionsEnabled === false ? (
          <div className="small danger">実行は無効です：backend起動時に <span className="mono">MANAOS_RPG_ENABLE_ACTIONS=1</span></div>
        ) : null}
        {filteredNextActions.length > 0 ? (
          <div>
            {filteredNextActions.map((x, i) => (
              <div key={i} className="small">- {x}</div>
            ))}
          </div>
        ) : (
          <div className="small">いまは平穏（危険度が上がると提案が出る）</div>
        )}

        {actionResult ? (
          <div style={{ marginTop: 10 }}>
            <div className="small">直近アクション結果</div>
            <div className="kv"><span>ID</span><span className="mono">{actionResult.action_id}</span></div>
            <div className="kv"><span>結果</span><span className={actionResult.result?.ok ? 'ok' : 'danger'}>{actionResult.result?.ok ? 'OK' : 'NG'}</span></div>
            {typeof actionResult.meta?.before_unified_rules === 'number' && typeof actionResult.meta?.after_unified_rules === 'number' ? (
              <div className="kv"><span>RULES</span><span className="mono">{actionResult.meta.before_unified_rules} → {actionResult.meta.after_unified_rules} (Δ{actionResult.meta.after_unified_rules - actionResult.meta.before_unified_rules})</span></div>
            ) : null}
            {typeof actionResult.result?.exit_code === 'number' ? (
              <div className="kv"><span>CODE</span><span className="mono">{actionResult.result.exit_code}</span></div>
            ) : null}
            {actionResult.result?.error ? (
              <div className="small danger">{actionResult.result.error}</div>
            ) : null}
            {actionResult.result?.stdout ? (
              <OutputBlock text={actionResult.result.stdout} />
            ) : null}
            {actionResult.result?.stderr ? (
              <OutputBlock text={actionResult.result.stderr} />
            ) : null}
          </div>
        ) : null}
      </Box>
    </div>
  )
}

function PartyView({ services }) {
  const raw = Array.isArray(services) ? services : []
  const list = useMemo(() => {
    return [...raw].sort((a, b) => {
      if (a.alive === b.alive) return 0
      return a.alive ? 1 : -1
    })
  }, [raw])
  return (
    <div>
      <div className="panelTitle">パーティ（サービス） <span className="small">{list.length}件</span></div>
      {list.length === 0 ? (
        <div className="small">サービスが未登録です（registry/services.yaml を追加）</div>
      ) : (
      <div className="table">
        <div className="tr th">
          <div>ID</div><div>NAME</div><div>KIND</div><div>PORT</div><div>STATUS</div><div>DETAIL</div>
        </div>
        {list.map((s) => (
          <div key={s.id} className="tr" style={s.alive ? undefined : { background: 'rgba(255,107,107,0.08)' }}>
            <div className="mono">{s.id}</div>
            <div>{s.name}</div>
            <div className="mono">{s.kind}</div>
            <div className="mono">{s.port ?? '—'}</div>
            <div className={s.alive ? 'ok' : 'danger'}>{s.alive ? 'ALIVE' : 'DOWN'}</div>
            <div className="small">
              <span className="mono">by={s.alive_by || '—'}</span>
              {typeof s.http_status === 'number' ? <span className="mono"> / http={s.http_status}</span> : null}
              {typeof s.docker_health === 'string' ? <span className={s.docker_health === 'unhealthy' ? 'danger' : 'small'}> / health={s.docker_health}</span> : null}
              {typeof s.docker_status === 'string' ? <span className="small"> / docker={s.docker_status}</span> : null}
              {typeof s.pm2_status === 'string' ? <span className={s.pm2_status === 'online' ? 'ok' : 'danger'}> / pm2={s.pm2_status}</span> : null}
              {typeof s.restart_count === 'number' ? <span className={s.restart_count >= 5 ? 'danger' : 'small'}> / restarts={s.restart_count}</span> : null}
              {Array.isArray(s.deps_down) && s.deps_down.length > 0 ? (
                <span className="danger"> / deps_down={s.deps_down.join(', ')}</span>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      )}
    </div>
  )
}

function BestiaryView({ models }) {
  const list = Array.isArray(models) ? models : []
  const [filterText, setFilterText] = useState('')

  const filtered = useMemo(() => {
    if (!filterText.trim()) return list
    const q = filterText.trim().toLowerCase()
    return list.filter((m) => {
      const haystack = [m?.id, m?.name, m?.type, m?.quant, ...(Array.isArray(m?.tags) ? m.tags : [])].join(' ').toLowerCase()
      return haystack.includes(q)
    })
  }, [list, filterText])

  const { byType, types } = useMemo(() => {
    const map = new Map()
    for (const m of filtered) {
      const t = String(m?.type || 'other')
      if (!map.has(t)) map.set(t, [])
      map.get(t).push(m)
    }
    const order = ['llm', 'image', 'video', 'voice', 'embedding', 'reranker', 'lora', 'other']
    const sorted = Array.from(map.keys()).sort((a, b) => {
      const ia = order.indexOf(a)
      const ib = order.indexOf(b)
      if (ia === -1 && ib === -1) return a.localeCompare(b)
      if (ia === -1) return 1
      if (ib === -1) return -1
      return ia - ib
    })
    return { byType: map, types: sorted }
  }, [filtered])

  return (
    <div>
      <div className="panelTitle">図鑑（モデル） <span className="small">{filtered.length}/{list.length}件 / {types.length}タイプ</span></div>
      <input className="input" value={filterText} onChange={(e) => setFilterText(e.target.value)} placeholder="フィルター（名前/ID/タグで絞り込み）" aria-label="モデルフィルター" style={{ marginBottom: 12, maxWidth: 400 }} />
      {list.length === 0 ? (
        <div className="small">モデルが見つかりません（Ollama / registry を確認）</div>
      ) : null}
      {types.map((t) => (
        <div key={t} className="sectionBlock">
          <div className="sectionHead">
            <span className="mono">TYPE</span>
            <span className="mono">{t.toUpperCase()}</span>
            <span className="small">{byType.get(t)?.length ?? 0}件</span>
          </div>
          <div className="table">
            <div className="tr th" style={{ gridTemplateColumns: '1.2fr 1.5fr 0.7fr 0.5fr 0.6fr 0.7fr 1.8fr' }}>
              <div>ID</div><div>NAME</div><div>TYPE</div><div>VER</div><div>QUANT</div><div>VRAM</div><div>TAGS</div>
            </div>
            {(byType.get(t) || []).map((m) => (
              <div key={m.id} className="tr" style={{ gridTemplateColumns: '1.2fr 1.5fr 0.7fr 0.5fr 0.6fr 0.7fr 1.8fr', ...(m.loaded ? { background: 'rgba(124,255,107,0.06)' } : {}) }}>
                <div className="mono">{m.id}</div>
                <div>{m.name}</div>
                <div className="mono">{m.type}</div>
                <div className="mono">{m.version ?? '—'}</div>
                <div className="mono">{m.quant ?? '—'}</div>
                <div className="mono">{m.vram_gb ?? '—'}GB</div>
                <div className="small">
                  {Array.isArray(m.tags) ? m.tags.join(', ') : '—'}
                  {typeof m.loaded === 'boolean' ? (
                    <span className={m.loaded ? 'ok' : 'small'}>{m.loaded ? ' / LOADED' : ' / idle'}</span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="small">PATH は backend の /api/registry で参照（運用上はパス漏洩に注意）</div>
    </div>
  )
}

function SkillsView({ skills, prompts, unifiedIntegrations, unifiedProxy, itemsRecent, apiBase, onRunAction, runningAction }) {
  const list = Array.isArray(skills) ? skills : []
  const ollamaTemplates = Array.isArray(prompts?.ollama) ? prompts.ollama : []
  const imageTemplates = Array.isArray(prompts?.image) ? prompts.image : []
  const videoTemplates = Array.isArray(prompts?.video) ? prompts.video : []

  const unifiedOk = Boolean(unifiedIntegrations?.ok)
  const unifiedData = unifiedOk && unifiedIntegrations?.data && typeof unifiedIntegrations.data === 'object'
    ? unifiedIntegrations.data
    : null

  const toolRows = useMemo(() => {
    const rows = []
    for (const s of list) {
      const items = Array.isArray(s?.items) ? s.items : []
      for (const it of items) {
        const typ = it?.url ? 'URL' : it?.action_id ? 'ACTION' : '—'
        const k = it?.integration_key
        let availability = 'UNKNOWN'
        let reason = ''
        if (k && !unifiedOk) {
          availability = 'AUTH'
        } else if (unifiedData && k && unifiedData?.[k]) {
          availability = unifiedData[k]?.available ? 'YES' : 'NO'
          reason = unifiedData[k]?.reason || ''
        }
        rows.push({
          cat: s?.label || s?.id,
          tool: it?.label || it?.id,
          type: typ,
          integrationKey: k || '',
          availability,
          reason
        })
      }
    }
    return rows
  }, [list, unifiedData])

  const [busyOp, setBusyOp] = useState('')

  const [ollamaModels, setOllamaModels] = useState([])
  const [ollamaModelErr, setOllamaModelErr] = useState('')
  const [ollamaModel, setOllamaModel] = useState('')
  const [ollamaTpl, setOllamaTpl] = useState('')
  const [ollamaPrompt, setOllamaPrompt] = useState('')
  const [ollamaOut, setOllamaOut] = useState('')

  const [imgTpl, setImgTpl] = useState('')
  const [imgPrompt, setImgPrompt] = useState('')
  const [imgNegative, setImgNegative] = useState('')
  const [imgResult, setImgResult] = useState('')

  const [videoTpl, setVideoTpl] = useState('')
  const [videoEndpoint, setVideoEndpoint] = useState('/api/unified/svi/generate')
  const [videoBody, setVideoBody] = useState('')
  const [videoOut, setVideoOut] = useState('')

  const recent = Array.isArray(itemsRecent) ? itemsRecent : []
  const mediaRecent = useMemo(() => {
    const okExt = new Set(['png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'mkv', 'gif'])
    return recent
      .filter((x) => okExt.has(String(x?.ext || '').toLowerCase()))
      .slice(0, 40)
  }, [recent])
  const [pickRel, setPickRel] = useState('')

  function itemUriFromPick() {
    if (!pickRel) return ''
    // pickRel is like: root_id|rel_path
    const [rootId, relPath] = String(pickRel).split('|')
    if (!rootId || !relPath) return ''
    return `item://${rootId}/${relPath}`
  }

  function tryInsertPathField(fieldName) {
    const uri = itemUriFromPick()
    if (!uri) return
    let obj = {}
    try {
      obj = videoBody && videoBody.trim() ? JSON.parse(videoBody) : {}
    } catch {
      setVideoOut('ERR: JSONが壊れてる（先に直してから差し込み）')
      return
    }
    obj = { ...obj, [fieldName]: uri }
    setVideoBody(JSON.stringify(obj, null, 2))
  }

  const [monitorOut, setMonitorOut] = useState('')

  const [memoryQuery, setMemoryQuery] = useState('')
  const [memoryScope, setMemoryScope] = useState('all')
  const [memoryLimit, setMemoryLimit] = useState(10)
  const [memoryOut, setMemoryOut] = useState('')

  const [notifyMsg, setNotifyMsg] = useState('')
  const [notifyPriority, setNotifyPriority] = useState('normal')
  const [notifyAsync, setNotifyAsync] = useState(true)
  const [notifyJobId, setNotifyJobId] = useState('')
  const [notifyOut, setNotifyOut] = useState('')

  const [memoryStoreContent, setMemoryStoreContent] = useState('')
  const [memoryStoreFormat, setMemoryStoreFormat] = useState('auto')
  const [memoryStoreMeta, setMemoryStoreMeta] = useState('')
  const [memoryStoreOut, setMemoryStoreOut] = useState('')

  const [routePrompt, setRoutePrompt] = useState('')
  const [routeContext, setRouteContext] = useState('')
  const [routePrefs, setRoutePrefs] = useState('')
  const [routeCodeContext, setRouteCodeContext] = useState('')
  const [routeOut, setRouteOut] = useState('')

  const [analyzePrompt, setAnalyzePrompt] = useState('')
  const [analyzeContext, setAnalyzeContext] = useState('')
  const [analyzeCodeContext, setAnalyzeCodeContext] = useState('')
  const [analyzeOut, setAnalyzeOut] = useState('')

  const proxyRules = Array.isArray(unifiedProxy?.rules) ? unifiedProxy.rules : []

  const openapi = unifiedIntegrations?.data?.openapi
  const openapiPathSet = useMemo(() => {
    const arr = Array.isArray(openapi?.paths_sample) ? openapi.paths_sample : []
    return new Set(arr)
  }, [openapi])
  const supportsPath = useCallback((p) => {
    const s = String(p || '')
    if (!s) return false
    if (openapiPathSet.has(s)) return true
    // OpenAPIが /api と非/api の両方を持つことがある
    if (s.startsWith('/api/') && openapiPathSet.has(s.replace('/api/', '/'))) return true
    if (s.startsWith('/') && openapiPathSet.has('/api' + s)) return true
    return false
  }, [openapiPathSet])

  const unifiedWriteEnabled = Boolean(unifiedProxy?.write_enabled)

  const [proxyId, setProxyId] = useState('')
  const [proxyQuery, setProxyQuery] = useState('')
  const [proxyBody, setProxyBody] = useState('')
  const [proxyOut, setProxyOut] = useState('')

  const proxyRule = useMemo(() => {
    const id = String(proxyId || '')
    return proxyRules.find((r) => String(r?.id) === id) || null
  }, [proxyRules, proxyId])

  const proxyRuleEnabled = proxyRule ? (proxyRule.enabled !== false) : true

  async function fetchMonitor(which) {
    setMonitorOut('')
    setBusyOp('monitor')
    try {
      const ent = MONITOR_ROUTES[String(which)]
      if (!ent?.path) {
        setMonitorOut('ERR: unknown route')
        return
      }
      if (ent.requires && !supportsPath(ent.requires)) {
        setMonitorOut(`UNSUPPORTED: Unified OpenAPI に ${ent.requires} が無い（いまのUnifiedでは未対応）`)
        return
      }
      const path = ent.path
      const r = await fetchJson(path)
      const text = JSON.stringify(r, null, 2)
      setMonitorOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setMonitorOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runMemoryRecall() {
    setMemoryOut('')
    setBusyOp('memory_recall')
    try {
      if (!supportsPath('/api/memory/search') && !supportsPath('/api/memory/recall')) {
        setMemoryOut('ERR: このUnified(OpenAPI)では memory 検索が未対応')
        return
      }
      const q = memoryQuery.trim()
      if (!q) {
        setMemoryOut('ERR: query is required')
        return
      }
      const scope = String(memoryScope || 'all')
      const lim = Math.max(1, Math.min(50, Number(memoryLimit || 10)))
      const qs = new URLSearchParams({ query: q, scope, limit: String(lim) }).toString()
      const r = await fetchJson(`/api/unified/memory/recall?${qs}`)
      const text = JSON.stringify(r, null, 2)
      setMemoryOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setMemoryOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runNotifySend() {
    setNotifyOut('')
    setBusyOp('notify_send')
    try {
      if (!unifiedWriteEnabled) {
        setNotifyOut('ERR: Unified write が無効（backendで MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 を設定）')
        return
      }
      const msg = notifyMsg.trim()
      if (!msg) {
        setNotifyOut('ERR: message is required')
        return
      }

      const payload = {
        message: msg,
        priority: String(notifyPriority || 'normal'),
        async: Boolean(notifyAsync)
      }

      const res = await fetch(`${apiBase}/api/unified/notify/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setNotifyOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      if (data?.data?.job_id) setNotifyJobId(String(data.data.job_id))
      const text = JSON.stringify(data, null, 2)
      setNotifyOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setNotifyOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runNotifyJob() {
    setNotifyOut('')
    setBusyOp('notify_job')
    try {
      if (!supportsPath('/api/ops/job/{job_id}') && !supportsPath('/ops/job/{job_id}')) {
        setNotifyOut('ERR: このUnified(OpenAPI)では job status が未対応')
        return
      }
      const jid = notifyJobId.trim()
      if (!jid) {
        setNotifyOut('ERR: job_id is required')
        return
      }
      const r = await fetchJson(`/api/unified/notify/job/${encodeURIComponent(jid)}`)
      const text = JSON.stringify(r, null, 2)
      setNotifyOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setNotifyOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runMemoryStore() {
    setMemoryStoreOut('')
    setBusyOp('memory_store')
    try {
      if (!unifiedWriteEnabled) {
        setMemoryStoreOut('ERR: Unified write が無効（backendで MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 を設定）')
        return
      }
      const content = memoryStoreContent.trim()
      if (!content) {
        setMemoryStoreOut('ERR: content is required')
        return
      }

      let metaObj = undefined
      if (memoryStoreMeta && memoryStoreMeta.trim()) {
        try {
          metaObj = JSON.parse(memoryStoreMeta)
        } catch {
          setMemoryStoreOut('ERR: metadata JSONが壊れてる')
          return
        }
      }

      const payload = {
        content,
        format_type: String(memoryStoreFormat || 'auto'),
        ...(metaObj ? { metadata: metaObj } : {})
      }

      const res = await fetch(`${apiBase}/api/unified/memory/store`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setMemoryStoreOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const text = JSON.stringify(data, null, 2)
      setMemoryStoreOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setMemoryStoreOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runRouteEnhanced() {
    setRouteOut('')
    setBusyOp('route')
    try {
      if (!supportsPath('/api/llm/route-enhanced')) {
        setRouteOut('ERR: このUnified(OpenAPI)では /api/llm/route-enhanced が未対応')
        return
      }
      const prompt = routePrompt.trim()
      if (!prompt) {
        setRouteOut('ERR: prompt is required')
        return
      }
      let contextObj = undefined
      let prefsObj = undefined
      if (routeContext && routeContext.trim()) {
        try {
          contextObj = JSON.parse(routeContext)
        } catch {
          setRouteOut('ERR: context JSONが壊れてる')
          return
        }
      }
      if (routePrefs && routePrefs.trim()) {
        try {
          prefsObj = JSON.parse(routePrefs)
        } catch {
          setRouteOut('ERR: preferences JSONが壊れてる')
          return
        }
      }

      const payload = {
        prompt,
        ...(contextObj ? { context: contextObj } : {}),
        ...(prefsObj ? { preferences: prefsObj } : {}),
        ...(routeCodeContext && routeCodeContext.trim() ? { code_context: routeCodeContext } : {})
      }

      const res = await fetch(`${apiBase}/api/unified/llm/route-enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setRouteOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const text = JSON.stringify(data, null, 2)
      setRouteOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setRouteOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runLlmAnalyze() {
    setAnalyzeOut('')
    setBusyOp('analyze')
    try {
      if (!supportsPath('/api/llm/analyze')) {
        setAnalyzeOut('ERR: このUnified(OpenAPI)では /api/llm/analyze が未対応')
        return
      }
      const prompt = analyzePrompt.trim()
      if (!prompt) {
        setAnalyzeOut('ERR: prompt is required')
        return
      }

      let contextObj = undefined
      if (analyzeContext && analyzeContext.trim()) {
        try {
          contextObj = JSON.parse(analyzeContext)
        } catch {
          setAnalyzeOut('ERR: context JSONが壊れてる')
          return
        }
      }

      const payload = {
        prompt,
        ...(contextObj ? { context: contextObj } : {}),
        ...(analyzeCodeContext && analyzeCodeContext.trim() ? { code_context: analyzeCodeContext } : {})
      }

      const res = await fetch(`${apiBase}/api/unified/llm/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setAnalyzeOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const text = JSON.stringify(data, null, 2)
      setAnalyzeOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setAnalyzeOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runUnifiedProxy() {
    setProxyOut('')
    setBusyOp('proxy')
    try {
      const id = proxyId.trim()
      if (!id) {
        setProxyOut('ERR: select a proxy rule')
        return
      }

      let q = {}
      if (proxyQuery && proxyQuery.trim()) {
        try {
          q = JSON.parse(proxyQuery)
        } catch {
          setProxyOut('ERR: query JSONが壊れてる')
          return
        }
      }
      if (q && typeof q !== 'object') {
        setProxyOut('ERR: query must be an object')
        return
      }

      let b = {}
      if (proxyBody && proxyBody.trim()) {
        try {
          b = JSON.parse(proxyBody)
        } catch {
          setProxyOut('ERR: body JSONが壊れてる')
          return
        }
      }
      if (b && typeof b !== 'object') {
        setProxyOut('ERR: body must be an object')
        return
      }

      const res = await fetch(`${apiBase}/api/unified/proxy/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, query: q, body: b })
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setProxyOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const text = JSON.stringify(data, null, 2)
      setProxyOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setProxyOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  function applyOllamaTemplate() {
    const t = ollamaTemplates.find((x) => String(x?.id) === String(ollamaTpl))
    const raw = String(t?.template || '')
    if (!raw) return
    setOllamaPrompt(raw.replace(/\{\{text\}\}/g, ''))
  }

  function applyImageTemplate() {
    const t = imageTemplates.find((x) => String(x?.id) === String(imgTpl))
    const p = String(t?.prompt || '')
    if (p) setImgPrompt(p)
    const n = String(t?.negative_prompt || '')
    if (typeof t?.negative_prompt !== 'undefined') setImgNegative(n)
  }

  function applyVideoTemplate() {
    const t = videoTemplates.find((x) => String(x?.id) === String(videoTpl))
    const ep = String(t?.endpoint || '').trim()
    if (ep) setVideoEndpoint(ep)
    const body = t?.body
    if (body && typeof body === 'object') {
      setVideoBody(JSON.stringify(body, null, 2))
    } else {
      setVideoBody('')
    }
  }

  async function runVideo() {
    setVideoOut('')
    setBusyOp('video')
    try {
      let payload = {}
      try {
        payload = videoBody && videoBody.trim() ? JSON.parse(videoBody) : {}
      } catch {
        setVideoOut('ERR: JSONが壊れてる')
        return
      }

      const res = await fetch(`${apiBase}${videoEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setVideoOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      setVideoOut(JSON.stringify(data, null, 2))
    } catch (e) {
      setVideoOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  useEffect(() => {
    fetchJson('/api/ollama/tags')
      .then((r) => {
        const models = (r?.data?.models || []).map((m) => m?.name).filter(Boolean)
        setOllamaModels(models)
        setOllamaModelErr('')
        if (!ollamaModel && models.length) setOllamaModel(models[0])
      })
      .catch((e) => {
        setOllamaModelErr(`Ollamaモデル取得失敗: ${String(e?.message || e)}`)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function runOllama() {
    setOllamaOut('')
    setBusyOp('ollama')
    try {
      const res = await fetch(`${apiBase}/api/ollama/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: ollamaModel, prompt: ollamaPrompt })
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setOllamaOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      setOllamaOut(String(data.response || ''))
    } catch (e) {
      setOllamaOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function queueImage() {
    setImgResult('')
    setBusyOp('image')
    try {
      const res = await fetch(`${apiBase}/api/generate/image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: imgPrompt, negative_prompt: imgNegative, width: 768, height: 768, steps: 20, seed: -1 })
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setImgResult(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const pid = data?.data?.prompt_id
      setImgResult(pid ? `queued: prompt_id=${pid}` : `queued: ${JSON.stringify(data.data).slice(0, 300)}`)
    } catch (e) {
      setImgResult(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  return (
    <div>
      <div className="panelTitle">魔法（スキル）</div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">CHEATSHEET</span>
          <span>生成ツール早見表</span>
          <span className="small">（同じ生成でも入口が複数あるので、まずここを見る）</span>
        </div>
        <div className="boxBody">
          <div className="small">Unified integrations/status: {unifiedOk ? <span className="ok">OK</span> : <span className="danger">NG</span>}</div>
          <div className="table" style={{ marginTop: 10 }}>
            <div className="tr th" style={{ gridTemplateColumns: '1.5fr 2fr 0.7fr 1.2fr 1.5fr' }}>
              <div>CATEGORY</div><div>TOOL</div><div>TYPE</div><div>AVAILABLE</div><div>KEY</div>
            </div>
            {toolRows.map((r, i) => (
              <div key={i} className="tr" style={{ gridTemplateColumns: '1.5fr 2fr 0.7fr 1.2fr 1.5fr', ...(r.availability === 'NO' || r.availability === 'AUTH' ? { background: 'rgba(255,107,107,0.08)' } : {}) }}>
                <div>{r.cat}</div>
                <div>{r.tool}</div>
                <div className="mono">{r.type}</div>
                <div>
                  {r.availability === 'YES' ? <span className="ok">YES</span> : null}
                  {r.availability === 'NO' ? <span className="danger">NO</span> : null}
                  {r.availability === 'AUTH' ? <span className="caution">AUTH?</span> : null}
                  {r.availability === 'UNKNOWN' ? <span className="small">—</span> : null}
                  {r.availability === 'NO' && r.reason ? <span className="small"> / {r.reason}</span> : null}
                </div>
                <div className="mono">{r.integrationKey || '—'}</div>
              </div>
            ))}
          </div>
          {!unifiedOk ? <div className="small">※ KEY付きの可否が欲しい場合は RPG backend に `MANAOS_UNIFIED_API_KEY`（read-only可）を渡す</div> : null}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">QUICK</span>
          <span>ローカルLLM（Ollama）</span>
          <span className="small">/api/ollama/generate</span>
        </div>
        <div className="boxBody">
          {ollamaModelErr ? <div className="small danger" style={{ marginBottom: 6 }}>{ollamaModelErr}</div> : null}
          {ollamaTemplates.length ? (
            <div className="kv"><span>TEMPLATE</span>
              <span>
                <select value={ollamaTpl} onChange={(e) => setOllamaTpl(e.target.value)} aria-label="Ollamaテンプレート">
                  <option value="">(select)</option>
                  {ollamaTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link ml" onClick={applyOllamaTemplate} disabled={!ollamaTpl}>適用</button>
              </span>
            </div>
          ) : null}
          <div className="kv"><span>MODEL</span>
            <span>
              <select value={ollamaModel} onChange={(e) => setOllamaModel(e.target.value)} aria-label="Ollamaモデル">
                {ollamaModels.length ? ollamaModels.map((m) => <option key={m} value={m}>{m}</option>) : <option value="">(no models)</option>}
              </select>
            </span>
          </div>
          <textarea className="input" rows={4} value={ollamaPrompt} onChange={(e) => setOllamaPrompt(e.target.value)} placeholder="ここに質問や指示（例：要約して、案を出して、など）" aria-label="Ollamaプロンプト" />
          <div className="skillActions">
            <button className="link" onClick={runOllama} disabled={!!busyOp || !ollamaModel || !ollamaPrompt.trim()}>{busyOp === 'ollama' ? '実行中…' : '実行'}</button>
          </div>
          {ollamaOut ? <OutputBlock text={ollamaOut} onClear={() => setOllamaOut('')} /> : <div className="small">結果はここに出る（OpenWebUIも併用OK）</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">QUICK</span>
          <span>画像生成（ComfyUI/統合API経由）</span>
          <span className="small">/api/generate/image</span>
        </div>
        <div className="boxBody">
          {imageTemplates.length ? (
            <div className="kv"><span>TEMPLATE</span>
              <span>
                <select value={imgTpl} onChange={(e) => setImgTpl(e.target.value)} aria-label="画像テンプレート">
                  <option value="">(select)</option>
                  {imageTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link ml" onClick={applyImageTemplate} disabled={!imgTpl}>適用</button>
              </span>
            </div>
          ) : null}
          <textarea className="input" rows={3} value={imgPrompt} onChange={(e) => setImgPrompt(e.target.value)} placeholder="画像プロンプト（例：a cozy room, cinematic light, masterpiece）" aria-label="画像プロンプト" />
          <textarea className="input" rows={2} value={imgNegative} onChange={(e) => setImgNegative(e.target.value)} placeholder="ネガティブ（任意）" aria-label="ネガティブプロンプト" />
          <div className="skillActions">
            <button className="link" onClick={queueImage} disabled={!!busyOp || !imgPrompt.trim()}>{busyOp === 'image' ? '投入中…' : 'キュー投入'}</button>
            <span className="small">生成物は「アイテム🎒」に出る</span>
          </div>
          {imgResult ? <div className="small">{imgResult}</div> : null}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">QUICK</span>
          <span>監視（キュー/履歴/最近の画像）</span>
          <span className="small">統合APIをRPG backend経由で参照</span>
        </div>
        <div className="boxBody">
          <div className="skillActions" style={{ flexWrap: 'wrap' }}>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('comfyui_queue')}>{busyOp === 'monitor' ? '…' : 'ComfyUI queue'}</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('comfyui_history')}>ComfyUI history</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('svi_queue')}>SVI queue</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('svi_history')}>SVI history</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('ltx2_queue')}>LTX2 queue</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('ltx2_history')}>LTX2 history</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('images_recent')}>images recent</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('llm_health')}>LLM health</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('llm_models')}>LLM models</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('unified_openapi')}>Unified OpenAPI</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('unified_proxy_doctor')}>Proxy Doctor</button>
            <span className="small">AUTH? が出る場合は `MANAOS_UNIFIED_API_KEY` を設定</span>
          </div>
          {monitorOut ? <OutputBlock text={monitorOut} onClear={() => setMonitorOut('')} /> : <div className="small">ここにJSONを表示（エラーも含む）</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">UNIFIED</span>
          <span>allowlist 実行器（GET/POST）</span>
          <span className="small">registry/unified_proxy.yaml 駆動</span>
        </div>
        <div className="boxBody">
          {proxyRules.length === 0 ? (
            <div className="small">allowlist が空：registry/unified_proxy.yaml の rules を追加</div>
          ) : (
            <div>
              <div className="kv"><span>RULE</span>
                <span>
                  <select value={proxyId} onChange={(e) => setProxyId(e.target.value)} aria-label="Proxyルール">
                    <option value="">(select)</option>
                    {proxyRules.map((r) => (
                      <option key={r.id} value={r.id}>{(r.enabled === false ? '[DISABLED] ' : '') + (r.label || r.id)}</option>
                    ))}
                  </select>
                </span>
              </div>
              {proxyRule ? (
                <div className="small">
                  <span className="mono">{String(proxyRule.method || 'GET')}</span>
                  <span className="mono ml">{String(proxyRule.path || '')}</span>
                  <span className={`${String(proxyRule.gate || 'read') === 'danger' ? 'danger' : 'small'} ml`}>
                    gate={String(proxyRule.gate || 'read')}
                  </span>
                  {proxyRule.enabled === false ? <span className="danger ml">DISABLED</span> : null}
                </div>
              ) : null}

              <textarea
                className="input"
                rows={3}
                value={proxyQuery}
                onChange={(e) => setProxyQuery(e.target.value)}
                placeholder={'query（任意・JSON） 例: {"limit":30} / path params は {"job_id":"..."} で渡す'}
                aria-label="ProxyクエリJSON"
              />
              {proxyRule && String(proxyRule.method || '').toUpperCase() === 'POST' ? (
                <textarea className="input" rows={4} value={proxyBody} onChange={(e) => setProxyBody(e.target.value)} placeholder="body（任意・JSON）" aria-label="ProxyボディJSON" />
              ) : null}

              <div className="skillActions">
                <button className="link" onClick={runUnifiedProxy} disabled={!!busyOp || !proxyId.trim() || !proxyRuleEnabled}>{busyOp === 'proxy' ? '実行中…' : '実行'}</button>
                <span className="small">write/danger は backend の環境変数ゲートが必要</span>
              </div>
              {proxyOut ? <OutputBlock text={proxyOut} onClear={() => setProxyOut('')} /> : <div className="small">結果はここに出る（ok/status/data/error）</div>}
            </div>
          )}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">STATUS</span>
          <span>記憶 / 通知（安全ステータス）</span>
          <span className="small">integrations/status + memory recall</span>
        </div>
        <div className="boxBody">
          <div className="small">
            Unified: {unifiedOk ? <span className="ok">OK</span> : <span className="danger">NG</span>}
            {' / '}Memory Search: {supportsPath('/api/memory/search') ? <span className="ok">SUPPORTED</span> : <span className="danger">UNSUPPORTED</span>}
            {' / '}Notify: {supportsPath('/api/ops/notify') ? <span className="ok">SUPPORTED</span> : <span className="danger">UNSUPPORTED</span>}
            {' / '}write_gate: {unifiedWriteEnabled ? <span className="ok">ON</span> : <span className="caution">OFF</span>}
          </div>

          <div className="kv" style={{ marginTop: 10 }}><span>QUERY</span>
            <span>
              <input className="input" value={memoryQuery} onChange={(e) => setMemoryQuery(e.target.value)} placeholder="memory recall query（必須）" />
            </span>
          </div>
          <div className="kv"><span>SCOPE</span>
            <span>
              <select value={memoryScope} onChange={(e) => setMemoryScope(e.target.value)} aria-label="メモリスコープ">
                <option value="all">all</option>
                <option value="short">short</option>
                <option value="long">long</option>
              </select>
            </span>
          </div>
          <div className="kv"><span>LIMIT</span>
            <span>
              <input className="input" type="number" min={1} max={50} value={memoryLimit} onChange={(e) => setMemoryLimit(Number(e.target.value) || 1)} style={{ width: 120 }} />
            </span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runMemoryRecall} disabled={!!busyOp || !memoryQuery.trim()}>{busyOp === 'memory_recall' ? '検索中…' : 'recall（GET）'}</button>
            <span className="small">※ Unified APIの認証が必要（KEY未設定だとAUTH?）</span>
          </div>
          {memoryOut ? <OutputBlock text={memoryOut} onClear={() => setMemoryOut('')} /> : <div className="small">結果はここに出る</div>}

          <div className="hr" />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">MEMORY</span>
            <span>保存（POST）</span>
            <span className="small">/api/unified/memory/store</span>
          </div>
          <textarea className="input" rows={3} value={memoryStoreContent} onChange={(e) => setMemoryStoreContent(e.target.value)} placeholder="content（必須）" aria-label="メモリ保存内容" />
          <div className="kv"><span>FORMAT</span>
            <span>
              <select value={memoryStoreFormat} onChange={(e) => setMemoryStoreFormat(e.target.value)} aria-label="メモリ保存形式">
                <option value="auto">auto</option>
                <option value="memo">memo</option>
                <option value="conversation">conversation</option>
                <option value="note">note</option>
              </select>
            </span>
          </div>
          <textarea className="input" rows={3} value={memoryStoreMeta} onChange={(e) => setMemoryStoreMeta(e.target.value)} placeholder="metadata（任意・JSON）" aria-label="メモリメタデータJSON" />
          <div className="skillActions">
            <button className="link" onClick={runMemoryStore} disabled={!!busyOp || !memoryStoreContent.trim()}>{busyOp === 'memory_store' ? '保存中…' : '保存（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {memoryStoreOut ? <OutputBlock text={memoryStoreOut} onClear={() => setMemoryStoreOut('')} /> : <div className="small">結果はここに出る（memory_id）</div>}

          <div className="hr" />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">NOTIFY</span>
            <span>通知送信（POST）</span>
            <span className="small">/api/unified/notify/send</span>
          </div>

          <textarea className="input" rows={3} value={notifyMsg} onChange={(e) => setNotifyMsg(e.target.value)} placeholder="通知メッセージ（必須）" aria-label="通知メッセージ" />
          <div className="kv"><span>PRIORITY</span>
            <span>
              <select value={notifyPriority} onChange={(e) => setNotifyPriority(e.target.value)} aria-label="通知優先度">
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </span>
          </div>
          <div className="kv"><span>ASYNC</span>
            <span>
              <select value={notifyAsync ? '1' : '0'} onChange={(e) => setNotifyAsync(e.target.value === '1')} aria-label="非同期モード">
                <option value="1">true（queued）</option>
                <option value="0">false（sync）</option>
              </select>
            </span>
          </div>

          <div className="skillActions">
            <button className="link" onClick={runNotifySend} disabled={!!busyOp || !notifyMsg.trim()}>{busyOp === 'notify_send' ? '送信中…' : '送信（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>

          <div className="kv"><span>JOB ID</span>
            <span>
              <input className="input" value={notifyJobId} onChange={(e) => setNotifyJobId(e.target.value)} placeholder="notifyjob_..." />
            </span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runNotifyJob} disabled={!!busyOp || !notifyJobId.trim()}>{busyOp === 'notify_job' ? '確認中…' : 'ジョブ確認（GET）'}</button>
          </div>

          {notifyOut ? <OutputBlock text={notifyOut} onClear={() => setNotifyOut('')} /> : <div className="small">結果はここに出る（queued/sent/failed など）</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">QUICK</span>
          <span>LLM route-enhanced（POST）</span>
          <span className="small">/api/unified/llm/route-enhanced</span>
        </div>
        <div className="boxBody">
          <div className="small">難易度だけ見たい場合は下の analyze（LLM呼び出しなし）</div>
          <textarea className="input" rows={3} value={routePrompt} onChange={(e) => setRoutePrompt(e.target.value)} placeholder="prompt（必須）" aria-label="Routeプロンプト" />
          <textarea className="input" rows={3} value={routeCodeContext} onChange={(e) => setRouteCodeContext(e.target.value)} placeholder="code_context（任意・そのまま文字列）" aria-label="Routeコードコンテキスト" />
          <textarea className="input" rows={4} value={routeContext} onChange={(e) => setRouteContext(e.target.value)} placeholder="context（任意・JSON）" aria-label="RouteコンテキストJSON" />
          <textarea className="input" rows={4} value={routePrefs} onChange={(e) => setRoutePrefs(e.target.value)} placeholder="preferences（任意・JSON）" aria-label="RouteプリファレンスJSON" />
          <div className="skillActions">
            <button className="link" onClick={runRouteEnhanced} disabled={!!busyOp || !routePrompt.trim()}>{busyOp === 'route' ? '実行中…' : '実行（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {routeOut ? <OutputBlock text={routeOut} onClear={() => setRouteOut('')} /> : <div className="small">結果はここに出る（選ばれたモデル/ルート/理由など）</div>}

          <div className="hr" />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">ANALYZE</span>
            <span>難易度分析（POST）</span>
            <span className="small">/api/unified/llm/analyze</span>
          </div>
          <textarea className="input" rows={3} value={analyzePrompt} onChange={(e) => setAnalyzePrompt(e.target.value)} placeholder="prompt（必須）" aria-label="Analyzeプロンプト" />
          <textarea className="input" rows={3} value={analyzeCodeContext} onChange={(e) => setAnalyzeCodeContext(e.target.value)} placeholder="code_context（任意・そのまま文字列）" aria-label="Analyzeコードコンテキスト" />
          <textarea className="input" rows={3} value={analyzeContext} onChange={(e) => setAnalyzeContext(e.target.value)} placeholder="context（任意・JSON）" aria-label="AnalyzeコンテキストJSON" />
          <div className="skillActions">
            <button className="link" onClick={runLlmAnalyze} disabled={!!busyOp || !analyzePrompt.trim()}>{busyOp === 'analyze' ? '分析中…' : '分析（POST）'}</button>
          </div>
          {analyzeOut ? <OutputBlock text={analyzeOut} onClear={() => setAnalyzeOut('')} /> : <div className="small">difficulty_score / level / recommended_model が出る</div>}
        </div>
      </div>

      <div className="sectionBlock">
        <div className="sectionHead">
          <span className="mono">QUICK</span>
          <span>動画生成（POST）</span>
          <span className="small">SVI / LTX2（RPG backend経由）</span>
        </div>
        <div className="boxBody">
          {videoTemplates.length ? (
            <div className="kv"><span>TEMPLATE</span>
              <span>
                <select value={videoTpl} onChange={(e) => setVideoTpl(e.target.value)} aria-label="動画テンプレート">
                  <option value="">(select)</option>
                  {videoTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link ml" onClick={applyVideoTemplate} disabled={!videoTpl}>適用</button>
              </span>
            </div>
          ) : null}

          <div className="kv"><span>ENDPOINT</span>
            <span>
              <select value={videoEndpoint} onChange={(e) => setVideoEndpoint(e.target.value)} aria-label="動画エンドポイント">
                <option value="/api/unified/svi/generate">/api/unified/svi/generate</option>
                <option value="/api/unified/svi/extend">/api/unified/svi/extend</option>
                <option value="/api/unified/ltx2/generate">/api/unified/ltx2/generate</option>
                <option value="/api/unified/ltx2-infinity/generate">/api/unified/ltx2-infinity/generate</option>
              </select>
            </span>
          </div>

          {mediaRecent.length ? (
            <div className="kv"><span>ITEMS</span>
              <span>
                <select value={pickRel} onChange={(e) => setPickRel(e.target.value)} aria-label="メディアピッカー">
                  <option value="">(recent images/videos)</option>
                  {mediaRecent.map((x, i) => {
                    const v = `${x.root_id}|${x.rel_path}`
                    const label = `${x.ext?.toUpperCase?.() || x.ext} / ${x.root_id}/${x.rel_path}`
                    return <option key={i} value={v}>{label}</option>
                  })}
                </select>
                <button className="link ml" onClick={() => tryInsertPathField('start_image_path')} disabled={!pickRel}>start_imageへ</button>
                <button className="link ml" onClick={() => tryInsertPathField('previous_video_path')} disabled={!pickRel}>prev_videoへ</button>
              </span>
            </div>
          ) : (
            <div className="small">recent items が空：先に何か生成/保存して「アイテム🎒」に出す</div>
          )}

          <textarea className="input" rows={8} value={videoBody} onChange={(e) => setVideoBody(e.target.value)} placeholder="ここにJSONボディ（テンプレ適用→編集）" aria-label="動画生成JSONボディ" />
          <div className="skillActions">
            <button className="link" onClick={runVideo} disabled={!!busyOp || !videoEndpoint}>{busyOp === 'video' ? '実行中…' : '実行（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {videoOut ? <OutputBlock text={videoOut} onClear={() => setVideoOut('')} /> : <div className="small">結果はここに出る（prompt_id / success / error）</div>}
        </div>
      </div>

      {list.length === 0 ? (
        <div className="small">registry/skills.yaml を追加するとここに表示されます</div>
      ) : (
        <div>
          {list.map((s) => (
            <div key={s.id} className="skillBlock">
              <div className="skillHead">
                <span className="mono">{s.id}</span>
                <span>{s.label}</span>
                <span className="small">{Array.isArray(s.tags) ? s.tags.join(', ') : ''}</span>
              </div>
              <div className="skillItems">
                {(Array.isArray(s.items) ? s.items : []).map((it) => (
                  <div key={it.id} className="skillItem">
                    <div className="mono">{it.id}</div>
                    <div>
                      <div>
                        {it.label}
                        {it.integration_key && !unifiedOk ? (
                          <span className="caution" style={{ marginLeft: 10 }}>AUTH?</span>
                        ) : null}
                        {it.integration_key && unifiedData?.[it.integration_key] ? (
                          <span className={unifiedData[it.integration_key]?.available ? 'ok' : 'danger'} style={{ marginLeft: 10 }}>
                            {unifiedData[it.integration_key]?.available ? 'AVAILABLE' : 'UNAVAILABLE'}
                          </span>
                        ) : null}
                      </div>
                      <div className="small">{it.notes || ''}</div>
                      <div className="skillActions">
                        {typeof it.url === 'string' && it.url ? (
                          <a className="link" href={it.url} target="_blank" rel="noreferrer">開く</a>
                        ) : null}
                        {typeof it.action_id === 'string' && it.action_id ? (
                          <button className="link" disabled={!!runningAction} onClick={() => onRunAction?.(it.action_id)}>{runningAction === it.action_id ? '実行中…' : '実行'}</button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="small">台帳駆動：追記するだけでメニューが育つ</div>
    </div>
  )
}

function SystemsView({ unified, onRunAction, actionResult, actionsEnabled, runningAction }) {
  const base = unified?.base
  const r = unified?.integrations
  const ok = Boolean(r?.ok)
  const data = r?.data && typeof r.data === 'object' ? r.data : null

  const mrl = unified?.mrl_memory
  const mrlOk = Boolean(mrl?.ok)
  const mrlBase = mrl?.base
  const mrlHealth = mrl?.health && typeof mrl.health === 'object' ? mrl.health : null
  const mrlCfg = mrl?.metrics?.config && typeof mrl.metrics.config === 'object' ? mrl.metrics.config : null

  const health = data?.health && typeof data.health === 'object' ? data.health : null
  const openapi = data?.openapi && typeof data.openapi === 'object' ? data.openapi : null

  const rows = useMemo(() => {
    if (!data) return []
    return Object.entries(data).map(([k, v]) => ({
      key: k,
      name: v?.name,
      available: Boolean(v?.available),
      reason: v?.reason
    }))
  }, [data])

  return (
    <div>
      <div className="panelTitle">システム（統合）</div>
      <div className="small">Unified API: <span className="mono">{base || '—'}</span></div>
      <div className="small">integrations/status: {ok ? <span className="ok">OK</span> : <span className="danger">NG</span>} / auth_configured={String(Boolean(r?.auth_configured))}</div>
      {!ok ? (
        <div className="err">{String(r?.error || 'unavailable')}</div>
      ) : null}

      {health || openapi ? (
        <div className="sectionBlock" style={{ marginTop: 10 }}>
          <div className="sectionHead">
            <span className="mono">MCP</span>
            <span>Unified health / openapi</span>
            <span className="small">（現行: MCP API Server）</span>
          </div>
          <div className="boxBody">
            {health ? (
              <div>
                <div className="kv"><span>service</span><span className="mono">{String(health.service || '—')}</span></div>
                <div className="kv"><span>status</span><span className={String(health.status) === 'healthy' ? 'ok' : 'caution'}>{String(health.status || '—')}</span></div>
                {typeof health.mcp_available !== 'undefined' ? (
                  <div className="kv"><span>mcp</span><span className={health.mcp_available ? 'ok' : 'danger'}>{health.mcp_available ? 'available' : 'unavailable'}</span></div>
                ) : null}
              </div>
            ) : (
              <div className="small">health: —</div>
            )}

            {openapi ? (
              <div style={{ marginTop: 10 }}>
                <div className="kv"><span>title</span><span className="mono">{String(openapi.title || '—')}</span></div>
                <div className="kv"><span>version</span><span className="mono">{String(openapi.version || '—')}</span></div>
                <div className="kv"><span>paths</span><span className="mono">{String(openapi.paths_count ?? '—')}</span></div>
                {Array.isArray(openapi.paths_sample) && openapi.paths_sample.length ? (
                  <div className="small">sample: <span className="mono">{openapi.paths_sample.slice(0, 10).join(' , ')}</span></div>
                ) : null}
              </div>
            ) : (
              <div className="small" style={{ marginTop: 10 }}>openapi: —</div>
            )}
          </div>
        </div>
      ) : null}

      <div className="sectionBlock" style={{ marginTop: 10 }}>
        <div className="sectionHead">
          <span className="mono">MRL</span>
          <span>mrl-memory status</span>
          <span className="small">（Unified memory 503時のフォールバック）</span>
        </div>
        <div className="boxBody">
          <div className="small">base: <span className="mono">{String(mrlBase || '—')}</span></div>
          <div className="small">health: {mrlOk ? <span className="ok">OK</span> : <span className="danger">NG</span>}</div>
          {mrlHealth ? (
            <div style={{ marginTop: 8 }}>
              <div className="kv"><span>service</span><span className="mono">{String(mrlHealth.service || '—')}</span></div>
              <div className="kv"><span>status</span><span className={String(mrlHealth.status) === 'healthy' ? 'ok' : 'caution'}>{String(mrlHealth.status || '—')}</span></div>
              {typeof mrlHealth.auth_required !== 'undefined' ? (
                <div className="kv"><span>auth</span><span className="mono">{String(mrlHealth.auth_required)}</span></div>
              ) : null}
            </div>
          ) : null}
          {mrlCfg ? (
            <div style={{ marginTop: 8 }}>
              <div className="kv"><span>write_mode</span><span className="mono">{String(mrlCfg.write_mode || '—')}</span></div>
              <div className="kv"><span>write_enabled</span><span className="mono">{String(mrlCfg.write_enabled || '—')}</span></div>
            </div>
          ) : null}

          <div className="skillActions" style={{ marginTop: 10 }}>
            <button
              className="link"
              disabled={actionsEnabled === false || !!runningAction}
              onClick={() => onRunAction?.('mrl_memory_write_on_full')}
            >
              {runningAction === 'mrl_memory_write_on_full' ? '実行中…' : '書き込みON（full）'}
            </button>
            <button
              className="link"
              disabled={actionsEnabled === false || !!runningAction}
              onClick={() => onRunAction?.('mrl_memory_write_off')}
            >
              {runningAction === 'mrl_memory_write_off' ? '実行中…' : '書き込みOFF（readonly）'}
            </button>
            {actionsEnabled === false ? <span className="caution">actions disabled</span> : null}
          </div>

          {actionResult?.action_id === 'mrl_memory_write_on_full' || actionResult?.action_id === 'mrl_memory_write_off' ? (
            <div className="sectionBlock" style={{ marginTop: 8 }}>
              <div className="small">last action: <span className="mono">{String(actionResult.action_id || '—')}</span></div>
              <div className="small">ok: {String(Boolean(actionResult?.result?.ok))}</div>
            </div>
          ) : null}
        </div>
      </div>

      {rows.length > 0 ? (
        <div className="sectionBlock" style={{ marginTop: 10 }}>
          <div className="sectionHead">
            <span className="mono">INTEGRATIONS</span>
            <span>サービス一覧</span>
            <span className="small">{rows.length}件</span>
          </div>
          <div className="table">
            <div className="tr th" style={{ gridTemplateColumns: '1.5fr 2fr 0.8fr 2.5fr' }}>
              <div>KEY</div><div>NAME</div><div>AVAILABLE</div><div>REASON</div>
            </div>
            {rows.map((x) => (
              <div key={x.key} className="tr" style={{ gridTemplateColumns: '1.5fr 2fr 0.8fr 2.5fr', ...(x.available ? {} : { background: 'rgba(255,107,107,0.08)' }) }}>
                <div className="mono">{x.key}</div>
                <div>{x.name || '—'}</div>
                <div className={x.available ? 'ok' : 'danger'}>{x.available ? 'YES' : 'NO'}</div>
                <div className="small">{x.reason || '—'}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="small" style={{ marginTop: 10 }}>データなし（APIキー未設定/認証NG の可能性）</div>
      )}
      <div className="small">必要なら環境変数で <span className="mono">MANAOS_UNIFIED_API_KEY</span>（または <span className="mono">MANAOS_INTEGRATION_READONLY_API_KEY</span>）をRPG backend側に渡す</div>
    </div>
  )
}

function QuestsView({ quests, apiBase, onRunAction, actionResult, runningAction }) {
  const list = Array.isArray(quests) ? quests : []
  const [questLoading, setQuestLoading] = useState('')
  const [questResult, setQuestResult] = useState(null)

  async function runApiQuest(endpoint) {
    setQuestLoading(endpoint)
    setQuestResult(null)
    try {
      const r = await fetchJson(endpoint)
      const text = JSON.stringify(r, null, 2)
      setQuestResult({ endpoint, text: text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text, ok: true })
    } catch (e) {
      setQuestResult({ endpoint, text: `ERR: ${String(e?.message || e)}`, ok: false })
    } finally {
      setQuestLoading('')
    }
  }
  return (
    <div>
      <div className="panelTitle">クエスト（タスク） <span className="small">{list.length}件</span></div>
      <div className="small">kind=api はクリック（GET）/ kind=action は実行（POST, backendで許可されたもののみ）</div>
      {actionResult ? (
        <div className="box" style={{ marginBottom: 12 }}>
          <div className="boxTitle">直近アクション結果</div>
          <div className="boxBody">
            <div className="kv"><span>ID</span><span className="mono">{actionResult.action_id}</span></div>
            <div className="kv"><span>結果</span><span className={actionResult.result?.ok ? 'ok' : 'danger'}>{actionResult.result?.ok ? 'OK' : 'NG'}</span></div>
            {typeof actionResult.result?.exit_code === 'number' ? (
              <div className="kv"><span>CODE</span><span className="mono">{actionResult.result.exit_code}</span></div>
            ) : null}
            {actionResult.result?.error ? (
              <div className="small danger">{actionResult.result.error}</div>
            ) : null}
          </div>
        </div>
      ) : null}
      <div className="table">
        <div className="tr th" style={{ gridTemplateColumns: '1.2fr 2fr 0.8fr 1.5fr 0.8fr' }}>
          <div>ID</div><div>LABEL</div><div>KIND</div><div>ENDPOINT</div><div>ACTION</div>
        </div>
        {list.map((q) => (
          <div key={q.id} className="tr" style={{ gridTemplateColumns: '1.2fr 2fr 0.8fr 1.5fr 0.8fr' }}>
            <div className="mono">{q.id}</div>
            <div>{q.label}</div>
            <div className="mono">{q.kind}</div>
            <div className="mono">{q.endpoint ?? q.action_id ?? '—'}</div>
            <div>
              {q.kind === 'api' && q.endpoint ? (
                <button className="link" disabled={!!questLoading} onClick={() => runApiQuest(q.endpoint)}>
                  {questLoading === q.endpoint ? '実行中…' : '実行'}
                </button>
              ) : q.kind === 'action' && q.action_id ? (
                <button className="link" disabled={!!runningAction} onClick={() => onRunAction?.(q.action_id)}>{runningAction === q.action_id ? '実行中…' : '実行'}</button>
              ) : (
                <span className="small">—</span>
              )}
            </div>
          </div>
        ))}
      </div>
      {questResult ? (
        <div style={{ marginTop: 12 }}>
          <div className="small">結果: <span className="mono">{questResult.endpoint}</span></div>
          <OutputBlock text={questResult.text} onClear={() => setQuestResult(null)} />
        </div>
      ) : null}
    </div>
  )
}

function LogsView({ events, onRefresh }) {
  const list = Array.isArray(events) ? events : []
  const [logFilter, setLogFilter] = useState('')
  const [logTypeFilter, setLogTypeFilter] = useState('')

  const logTypes = useMemo(() => {
    const s = new Set()
    for (const e of list) if (e?.type) s.add(String(e.type).toUpperCase())
    return Array.from(s).sort()
  }, [list])

  const filtered = useMemo(() => {
    let out = list
    if (logTypeFilter) {
      out = out.filter((e) => String(e?.type || '').toUpperCase() === logTypeFilter)
    }
    if (logFilter.trim()) {
      const q = logFilter.trim().toLowerCase()
      out = out.filter((e) => String(e?.message || '').toLowerCase().includes(q) || String(e?.type || '').toLowerCase().includes(q))
    }
    return out
  }, [list, logFilter, logTypeFilter])

  const reversed = useMemo(() => filtered.slice().reverse(), [filtered])

  return (
    <div>
      <div className="panelTitleRow">
        <span>戦闘ログ</span>
        <button className="link" onClick={onRefresh}>再読込</button>
        <span className="small">{filtered.length}/{list.length}件</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <input className="input" value={logFilter} onChange={(e) => setLogFilter(e.target.value)} placeholder="テキストで絞り込み" aria-label="ログ検索" style={{ marginTop: 0, maxWidth: 280 }} />
        <select value={logTypeFilter} onChange={(e) => setLogTypeFilter(e.target.value)} aria-label="ログタイプフィルター" style={{ padding: '4px 6px' }}>
          <option value="">全タイプ</option>
          {logTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="log">
        {filtered.length === 0 ? (
          <div className="small">{list.length === 0 ? 'events.log がまだ空です（サービスダウン等で自動追記）' : 'フィルターに一致するログがありません'}</div>
        ) : (
          reversed.map((e, idx) => (
            <div key={`${e.ts}-${e.type}-${idx}`} className="logLine">
              <span className="mono">{fmtTs(e.ts)}</span>
              <span className={`mono ${logTypeCls(e.type)}`}>[{e.type}]</span>
              <span>{e.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function MapView({ devices }) {
  const list = Array.isArray(devices) ? devices : []
  const aliveDevices = useMemo(() => list.filter((d) => d.alive), [list])
  return (
    <div>
      <div className="panelTitle">マップ（デバイス） <span className="small">{list.length}件{list.length > 0 ? ` / ${aliveDevices.length} online` : ''}</span></div>
      {list.length === 0 ? (
        <div className="small">デバイスが未登録です（registry/devices.yaml を追加）</div>
      ) : (
        <div className="table">
          <div className="tr th" style={{ gridTemplateColumns: '1.2fr 2fr 1fr 0.8fr 2fr' }}>
            <div>ID</div><div>NAME</div><div>KIND</div><div>STATUS</div><div>TAGS</div>
          </div>
          {list.map((d) => (
            <div key={d.id} className="tr" style={{ gridTemplateColumns: '1.2fr 2fr 1fr 0.8fr 2fr', ...(typeof d.alive === 'boolean' && !d.alive ? { background: 'rgba(255,107,107,0.08)' } : {}) }}>
              <div className="mono">{d.id}</div>
              <div>{d.name}</div>
              <div className="mono">{d.kind}</div>
              <div>{typeof d.alive === 'boolean' ? <span className={d.alive ? 'ok' : 'danger'}>{d.alive ? 'ONLINE' : 'OFFLINE'}</span> : <span className="small">—</span>}</div>
              <div className="small">{Array.isArray(d.tags) ? d.tags.join(', ') : '—'}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ItemsView({ items, apiBase }) {
  const recent = Array.isArray(items?.recent) ? items.recent : []
  const roots = Array.isArray(items?.roots) ? items.roots : []
  const [brokenImgs, setBrokenImgs] = useState(() => new Set())
  const [expandedGroups, setExpandedGroups] = useState(() => new Set())

  const labelById = useMemo(() => new Map(roots.map((r) => [r.id, r.label])), [roots])

  const { grouped, groupKeys } = useMemo(() => {
    const map = new Map()
    for (const it of recent) {
      const rid = String(it?.root_id || 'unknown')
      if (!map.has(rid)) map.set(rid, [])
      map.get(rid).push(it)
    }
    const keys = Array.from(map.keys()).sort((a, b) => {
      const la = labelById.get(a) || a
      const lb = labelById.get(b) || b
      return String(la).localeCompare(String(lb))
    })
    return { grouped: map, groupKeys: keys }
  }, [recent, labelById])

  return (
    <div>
      <div className="panelTitle">アイテム（生成物） <span className="small">{recent.length}件</span></div>
      <div className="small">監視フォルダ: {roots.length ? roots.map((r) => r.label).join(' / ') : '未設定（registry/items.yaml）'}</div>

      {recent.length === 0 ? (
        <div className="small">生成物が見つかりません（registry/items.yaml の path を実フォルダに合わせてね）</div>
      ) : (
        <div>
          {groupKeys.map((rid) => (
            <div key={rid} className="sectionBlock">
              <div className="sectionHead">
                <span className="mono">ROOT</span>
                <span>{labelById.get(rid) || rid}</span>
                <span className="small">{grouped.get(rid)?.length ?? 0}件</span>
              </div>
              <div className="itemsGrid">
                {(() => {
                  const groupItems = grouped.get(rid) || []
                  const expanded = expandedGroups.has(rid)
                  const limit = expanded ? groupItems.length : 24
                  const visible = groupItems.slice(0, limit)
                  return (
                    <>
                      {visible.map((it, idx) => {
                        const url = `${apiBase}/files/${encodeURIComponent(it.root_id)}/${encodeRelPath(it.rel_path)}`
                        return (
                          <div key={`${it.root_id}:${it.rel_path}:${idx}`} className="itemCard">
                            <div className="itemHead">
                              <div className="mono">{it.kind}</div>
                              <div className="small">{fmtTs(it.mtime)} / {fmtBytes(it.size_bytes)}</div>
                            </div>
                            <div className="itemBody">
                              {it.kind === 'image' ? (
                                brokenImgs.has(`${it.root_id}:${it.rel_path}`) ? (
                                  <span className="small">画像読込失敗</span>
                                ) : (
                                  <a href={url} target="_blank" rel="noreferrer" className="itemMedia">
                                    <img src={url} alt={it.name} loading="lazy" onError={() => setBrokenImgs((prev) => new Set(prev).add(`${it.root_id}:${it.rel_path}`))} />
                                  </a>
                                )
                              ) : it.kind === 'video' ? (
                                <video className="itemVideo" src={url} controls preload="metadata" />
                              ) : (
                                <a className="link" href={url} target="_blank" rel="noreferrer">開く</a>
                              )}
                            </div>
                            <div className="itemFoot">
                              <div className="small">{it.name}</div>
                              <div className="mono">{it.rel_path}</div>
                            </div>
                          </div>
                        )
                      })}
                      {!expanded && groupItems.length > 24 ? (
                        <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: 8 }}>
                          <button className="link" onClick={() => setExpandedGroups((prev) => new Set(prev).add(rid))}>
                            もっと見る（残り {groupItems.length - 24}件）
                          </button>
                        </div>
                      ) : null}
                    </>
                  )
                })()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
