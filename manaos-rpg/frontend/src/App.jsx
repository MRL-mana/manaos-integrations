import { useCallback, useEffect, useMemo, useRef, useState, Suspense, lazy } from 'react'
import { fetchJson, getApiBase } from './api.js'
import {
  TITLE_BASE, AUTO_REFRESH_MS, ERROR_DISMISS_MS, EVENTS_LIMIT,
  TICK_INTERVAL_MS, FALLBACK_MENU,
  fmtTs, fmtAgo, dangerRank
} from './utils.js'

import ErrorBoundary from './components/ErrorBoundary.jsx'
import SettingsView from './components/SettingsView.jsx'
import StatusView from './components/StatusView.jsx'
import PartyView from './components/PartyView.jsx'
import BestiaryView from './components/BestiaryView.jsx'
import QuestsView from './components/QuestsView.jsx'
import LogsView from './components/LogsView.jsx'
import MapView from './components/MapView.jsx'
import ItemsView from './components/ItemsView.jsx'
import SystemsView from './components/SystemsView.jsx'
import GlobalSearch from './components/GlobalSearch.jsx'
import HealthStrip from './components/HealthStrip.jsx'

/* React.lazy で大型コンポーネントを遅延読み込み (code-split) */
const RLView = lazy(() => import('./components/RLView.jsx'))
const SkillsView = lazy(() => import('./components/SkillsView.jsx'))
const RevenueView = lazy(() => import('./components/RevenueView.jsx'))

const TAB_IDS = ['status','party','bestiary','skills','quests','logs','map','items','rl','revenue','systems']

export default function App() {
  const [state, setState] = useState(null)
  const [events, setEvents] = useState([])
  const [active, setActive] = useState(() => {
    const hash = window.location.hash.replace('#', '')
    return TAB_IDS.includes(hash) ? hash : 'status'
  })
  const [err, setErr] = useState('')
  const [actionResult, setActionResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lastRefreshTs, setLastRefreshTs] = useState(null)
  const [tick, setTick] = useState(0)
  const [showHelp, setShowHelp] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState({ apiKey: '', refreshMs: 30000, theme: 'default' })
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

  const refreshAutonomy = useCallback(async function refreshAutonomy() {
    try {
      const autonomy = await fetchJson('/api/autonomy')
      setState((prev) => {
        if (!prev || typeof prev !== 'object') return prev
        return { ...prev, autonomy }
      })
    } catch {
    }
  }, [])

  const refreshState = useCallback(async function refreshState() {
    setErr('')
    setLoading(true)
    try {
      const st = await fetchJson('/api/state')
      setState(st)
      refreshAutonomy()
      setLastRefreshTs(Date.now())
    } catch (e) {
      try {
        const snap = await refreshSnapshot()
        if (!snap) setErr(String(e?.message || e))
      } catch {
        setErr(String(e?.message || e))
      }
    } finally {
      setLoading(false)
    }
  }, [refreshAutonomy, refreshSnapshot])

  const [runningAction, setRunningAction] = useState('')

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
    refreshState()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!err) return
    const id = setTimeout(() => setErr(''), ERROR_DISMISS_MS)
    return () => clearTimeout(id)
  }, [err])

  const refreshEvents = useCallback(() => {
    fetchJson(`/api/events?limit=${EVENTS_LIMIT}`)
      .then((r) => setEvents(r.events || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(() => {
      refreshState().then(() => {
        if (active === 'logs') refreshEvents()
      })
    }, AUTO_REFRESH_MS)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, active])

  useEffect(() => {
    if (active === 'logs') refreshEvents()
    panelRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
    window.location.hash = active
  }, [active, refreshEvents])

  /* hashchangeで戻る・進むに対応 */
  useEffect(() => {
    function onHashChange() {
      const h = window.location.hash.replace('#', '')
      if (TAB_IDS.includes(h)) setActive(h)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), TICK_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    function handleKey(e) {
      /* Ctrl+K: ヘルプが開いていたら閉じる */
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        setShowHelp(false)
        return // GlobalSearch側で処理
      }

      const tag = e.target?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      if (e.key === '0') {
        e.preventDefault()
        setActive(TAB_IDS[9])
        return
      }
      const num = parseInt(e.key, 10)
      if (num >= 1 && num <= 9) {
        e.preventDefault()
        setActive(TAB_IDS[num - 1])
        return
      }
      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        refreshSnapshot()
      }
      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault()
        setShowHelp(prev => !prev)
      }
      if (e.key === 'Escape') {
        setErr('')
        setShowHelp(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [refreshSnapshot])

  const menu = Array.isArray(state?.menu) ? state.menu : FALLBACK_MENU

  const rank = dangerRank(state?.danger)

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

  const services = state?.services
  const aliveCount = useMemo(() => {
    const svcs = Array.isArray(services) ? services : []
    return svcs.filter((s) => s.alive).length
  }, [services])
  const totalCount = Array.isArray(services) ? services.length : 0

  const lazyFallback = <div className="loading">読み込み中…</div>

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
          <span title="1-9,0: タブ切替 / R: 更新 / Esc: エラー閉じる / Ctrl+K: 検索">⌨ ショートカット有</span>
        </div>
        <HealthStrip services={state?.services} />
        <div className="actions">
          <button className="settingsBtn" onClick={() => setShowSettings(true)} title="設定">⚙</button>
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
          <div className="err errRow" role="alert">
            <span>{err}</span>
            <button className="link" onClick={() => setErr('')} aria-label="エラーを閉じる">✕</button>
          </div>
        ) : null}
      </header>

      <main className="main">
        <nav className="menu" aria-label="メインメニュー" role="tablist" aria-orientation="vertical"
          onKeyDown={(e) => {
            const ids = menu.map((m) => m.id)
            const idx = ids.indexOf(active)
            if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
              e.preventDefault()
              const next = ids[(idx + 1) % ids.length]
              setActive(next)
              e.currentTarget.querySelector(`[data-tab="${next}"]`)?.focus()
            } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
              e.preventDefault()
              const prev = ids[(idx - 1 + ids.length) % ids.length]
              setActive(prev)
              e.currentTarget.querySelector(`[data-tab="${prev}"]`)?.focus()
            } else if (e.key === 'Home') {
              e.preventDefault()
              setActive(ids[0])
              e.currentTarget.querySelector(`[data-tab="${ids[0]}"]`)?.focus()
            } else if (e.key === 'End') {
              e.preventDefault()
              setActive(ids[ids.length - 1])
              e.currentTarget.querySelector(`[data-tab="${ids[ids.length - 1]}"]`)?.focus()
            }
          }}
        >
          <div className="menuTitle">コマンド</div>
          {menu.map((m) => {
            /* メニューバッジ計算 */
            let badge = null
            if (m.id === 'party' && Array.isArray(state?.services)) {
              const alive = state.services.filter(s => s.alive).length
              badge = <span className={`menuBadge ${alive === 0 ? 'menuBadgeDanger' : ''}`}>{alive}/{state.services.length}</span>
            } else if (m.id === 'bestiary' && Array.isArray(state?.models)) {
              const loaded = state.models.filter(x => x.loaded).length
              badge = loaded > 0
                ? <span className="menuBadge menuBadgeOk">{loaded}</span>
                : <span className="menuBadge">{state.models.length}</span>
            } else if (m.id === 'map' && Array.isArray(state?.devices)) {
              const online = state.devices.filter(d => d.alive).length
              badge = <span className={`menuBadge ${online === state.devices.length ? 'menuBadgeOk' : 'menuBadgeDanger'}`}>{online}/{state.devices.length}</span>
            } else if (m.id === 'logs' && Array.isArray(events)) {
              badge = events.length > 0 ? <span className="menuBadge">{events.length > 99 ? '99+' : events.length}</span> : null
            } else if (m.id === 'systems') {
              const d = Number(state?.danger || 0)
              if (d > 0) badge = <span className="menuBadge menuBadgeDanger">⚠{d}</span>
            }
            return (
              <button
                key={m.id}
                data-tab={m.id}
                role="tab"
                aria-selected={m.id === active}
                aria-controls={`panel-${m.id}`}
                tabIndex={m.id === active ? 0 : -1}
                className={m.id === active ? 'menuItem active' : 'menuItem'}
                onClick={() => setActive(m.id)}
              >
                <span className="icon">{m.icon}</span>
                <span className="label">{m.label}</span>
                {badge}
              </button>
            )
          })}
        </nav>

        <section className="panel" ref={panelRef} role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`} tabIndex={0}>
          <div id="main-content">
          {!state && !err ? (
            <div className="loading">データを読み込み中…</div>
          ) : null}
          {state && active === 'status' ? (
            <StatusView
              host={state?.host}
              storage={state?.storage}
              google={state?.google}
              services={state?.services}
              models={state?.models}
              devices={state?.devices}
              skills={state?.skills}
              danger={state?.danger}
              rlAnything={state?.rl_anything}
              autonomy={state?.autonomy}
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
              <Suspense fallback={lazyFallback}>
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
              </Suspense>
            </div>
          ) : null}
          {state && active === 'quests' ? <QuestsView quests={state?.quests} apiBase={apiBase} onRunAction={runAction} actionResult={actionResult} runningAction={runningAction} /> : null}
          {state && active === 'logs' ? <LogsView events={events} onRefresh={refreshEvents} /> : null}
          {state && active === 'map' ? <MapView devices={state?.devices} /> : null}
          {state && active === 'items' ? <ItemsView items={state?.items} apiBase={apiBase} /> : null}
          {state && active === 'rl' ? (
            <Suspense fallback={lazyFallback}>
              <RLView rl={state?.rl_anything} apiBase={apiBase} />
            </Suspense>
          ) : null}
          {state && active === 'revenue' ? (
            <Suspense fallback={lazyFallback}>
              <RevenueView />
            </Suspense>
          ) : null}
          {state && active === 'systems' ? (
            <SystemsView
              unified={state?.unified}
              onRunAction={runAction}
              actionResult={actionResult}
              actionsEnabled={state?.actions_enabled}
              runningAction={runningAction}
            />
          ) : null}
          </div>
        </section>
      </main>
    </div>
    <GlobalSearch state={state} onNavigate={(tab) => setActive(tab)} />

    {/* 設定モーダル */}
    <SettingsView open={showSettings} config={settings} onSave={cfg => { setSettings(cfg); setShowSettings(false); }} onClose={() => setShowSettings(false)} />

    {/* ショートカットヘルプ */}
    {showHelp && (
      <div className="helpOverlay" onClick={() => setShowHelp(false)} role="dialog" aria-modal="true" aria-label="キーボードショートカット">
        <div className="helpModal" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === 'Tab') { const focusable = e.currentTarget.querySelectorAll('button'); const first = focusable[0]; const last = focusable[focusable.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus() } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() } } }}>
          <div className="helpTitle">⌨ キーボードショートカット</div>
          <div className="helpGrid">
            <kbd>1</kbd><span>ステータス</span>
            <kbd>2</kbd><span>パーティ</span>
            <kbd>3</kbd><span>図鑑</span>
            <kbd>4</kbd><span>魔法</span>
            <kbd>5</kbd><span>クエスト</span>
            <kbd>6</kbd><span>ログ</span>
            <kbd>7</kbd><span>マップ</span>
            <kbd>8</kbd><span>アイテム</span>
            <kbd>9</kbd><span>RL</span>
            <kbd>0</kbd><span>システム</span>
            <kbd>R</kbd><span>スナップショット更新</span>
            <kbd>Ctrl+K</kbd><span>グローバル検索</span>
            <kbd>?</kbd><span>このヘルプ</span>
            <kbd>Esc</kbd><span>閉じる</span>
          </div>
          <button className="helpClose" onClick={() => setShowHelp(false)}>閉じる</button>
        </div>
      </div>
    )}
    </ErrorBoundary>
  )
}
