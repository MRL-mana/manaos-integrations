import React, { useEffect, useMemo, useState } from 'react'
import { fetchJson, getApiBase } from './api.js'

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

export default function App() {
  const [state, setState] = useState(null)
  const [events, setEvents] = useState([])
  const [active, setActive] = useState('status')
  const [err, setErr] = useState('')
  const [actionResult, setActionResult] = useState(null)
  const apiBase = useMemo(() => getApiBase(), [])

  async function refreshSnapshot() {
    setErr('')
    try {
      const snap = await fetchJson('/api/snapshot')
      setState(snap)
      if (active === 'logs') {
        const e = await fetchJson('/api/events?limit=120')
        setEvents(e.events || [])
      }
      return snap
    } catch (e) {
      setErr(String(e?.message || e))
      return null
    }
  }

  async function refreshState() {
    setErr('')
    try {
      const st = await fetchJson('/api/state')
      setState(st)
    } catch (e) {
      setErr(String(e?.message || e))
    }
  }

  async function runAction(actionId) {
    setErr('')
    setActionResult(null)
    try {
      const beforeUnifiedRules = Array.isArray(state?.unified?.proxy?.rules) ? state.unified.proxy.rules.length : null
      const base = getApiBase()
      const res = await fetch(`${base}/api/actions/${encodeURIComponent(actionId)}/run`, {
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
    }
  }

  useEffect(() => {
    refreshSnapshot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (active === 'logs') {
      fetchJson('/api/events?limit=120')
        .then((r) => setEvents(r.events || []))
        .catch(() => {})
    }
  }, [active])

  const menu = Array.isArray(state?.menu) ? state.menu : [
    { id: 'status', label: 'ステータス', icon: '🧍' },
    { id: 'party', label: 'パーティ（サービス）', icon: '🧩' },
    { id: 'bestiary', label: '図鑑（モデル）', icon: '📚' },
    { id: 'skills', label: '魔法（スキル）', icon: '✨' },
    { id: 'quests', label: 'クエスト（タスク）', icon: '🗺' },
    { id: 'logs', label: '戦闘ログ', icon: '📜' },
    { id: 'map', label: 'マップ（デバイス）', icon: '🧭' },
    { id: 'items', label: 'アイテム（生成物）', icon: '🎒' },
    { id: 'systems', label: 'システム（統合）', icon: '⚙️' }
  ]

  const rank = dangerRank(state?.danger)

  return (
    <div className="screen">
      <header className="header">
        <div className="title">MANAOS // RPG COMMAND</div>
        <div className={`badge ${rank.cls}`}>危険度: {rank.label} ({Number(state?.danger || 0)})</div>
        <div className="meta">
          <span>API: {apiBase}</span>
          <span>更新: {fmtTs(state?.ts)}</span>
        </div>
        <div className="actions">
          <button onClick={refreshSnapshot}>更新（/api/snapshot）</button>
          <button onClick={refreshState}>読込（/api/state）</button>
        </div>
        {err ? <div className="err">{err}</div> : null}
      </header>

      <main className="main">
        <nav className="menu">
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

        <section className="panel">
          {active === 'status' ? (
            <StatusView
              host={state?.host}
              nextActions={state?.next_actions}
              nextActionHints={state?.next_action_hints}
              onRunAction={runAction}
              actionResult={actionResult}
              actionsEnabled={state?.actions_enabled}
            />
          ) : null}
          {active === 'party' ? <PartyView services={state?.services} /> : null}
          {active === 'bestiary' ? <BestiaryView models={state?.models} /> : null}
          {active === 'skills' ? (
            <SkillsView
              skills={state?.skills}
              prompts={state?.prompts}
              unifiedIntegrations={state?.unified?.integrations}
              unifiedProxy={state?.unified?.proxy}
              itemsRecent={state?.items?.recent}
              onRunAction={runAction}
            />
          ) : null}
          {active === 'quests' ? <QuestsView quests={state?.quests} apiBase={apiBase} onRunAction={runAction} actionResult={actionResult} /> : null}
          {active === 'logs' ? <LogsView events={events} /> : null}
          {active === 'map' ? <MapView devices={state?.devices} /> : null}
          {active === 'items' ? <ItemsView items={state?.items} apiBase={apiBase} /> : null}
          {active === 'systems' ? <SystemsView unified={state?.unified} /> : null}
        </section>
      </main>
    </div>
  )
}

function Box({ title, children }) {
  return (
    <div className="box">
      <div className="boxTitle">{title}</div>
      <div className="boxBody">{children}</div>
    </div>
  )
}

function StatusView({ host, nextActions, nextActionHints, onRunAction, actionResult, actionsEnabled }) {
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

  const suppressRules = []
  if (hints.some((h) => h?.action_id === 'unified_proxy_disable_404')) {
    suppressRules.push(/404自動無効化|台帳掃除|GET 404/)
  }
  if (hints.some((h) => h?.action_id === 'unified_proxy_sync')) {
    suppressRules.push(/allowlist.*同期|同期\/有効化|同期→/)
  }

  const filteredNextActions = suppressRules.length === 0
    ? actions
    : actions.filter((x) => !suppressRules.some((re) => re.test(String(x || ''))))

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
              <div className="small">
                UTIL {g.utilization_gpu ?? '—'}% / VRAM {g.mem_used_mb ?? '—'}MB / {g.mem_total_mb ?? '—'}MB / TEMP {g.temperature_c ?? '—'}C
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
        <div className="kv"><span>TX</span><span>{host?.net?.bytes_sent ?? '—'} bytes</span></div>
        <div className="kv"><span>RX</span><span>{host?.net?.bytes_recv ?? '—'} bytes</span></div>
      </Box>

      <Box title="次の一手">
        {hints.length > 0 ? (
          <div>
            {hints.map((h, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '10px',
                  marginBottom: '6px'
                }}
              >
                <div className="small">- {h?.label || '—'}</div>
                {h?.action_id ? (
                  <button className="link" disabled={actionsEnabled === false} onClick={() => onRunAction?.(h.action_id)}>実行</button>
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
              <pre className="output">{actionResult.result.stdout}</pre>
            ) : null}
            {actionResult.result?.stderr ? (
              <pre className="output">{actionResult.result.stderr}</pre>
            ) : null}
          </div>
        ) : null}
      </Box>
    </div>
  )
}

function PartyView({ services }) {
  const list = Array.isArray(services) ? services : []
  return (
    <div>
      <div className="panelTitle">パーティ（サービス）</div>
      <div className="table">
        <div className="tr th">
          <div>ID</div><div>NAME</div><div>KIND</div><div>PORT</div><div>STATUS</div><div>DETAIL</div>
        </div>
        {list.map((s) => (
          <div key={s.id} className="tr">
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
    </div>
  )
}

function BestiaryView({ models }) {
  const list = Array.isArray(models) ? models : []

  const byType = new Map()
  for (const m of list) {
    const t = String(m?.type || 'other')
    if (!byType.has(t)) byType.set(t, [])
    byType.get(t).push(m)
  }

  const order = ['llm', 'image', 'video', 'voice', 'embedding', 'reranker', 'lora', 'other']
  const types = Array.from(byType.keys()).sort((a, b) => {
    const ia = order.indexOf(a)
    const ib = order.indexOf(b)
    if (ia === -1 && ib === -1) return a.localeCompare(b)
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })

  return (
    <div>
      <div className="panelTitle">図鑑（モデル）</div>
      {types.map((t) => (
        <div key={t} className="sectionBlock">
          <div className="sectionHead">
            <span className="mono">TYPE</span>
            <span className="mono">{t.toUpperCase()}</span>
            <span className="small">{byType.get(t)?.length ?? 0}件</span>
          </div>
          <div className="table">
            <div className="tr th">
              <div>ID</div><div>NAME</div><div>TYPE</div><div>VER</div><div>QUANT</div><div>VRAM</div><div>TAGS</div>
            </div>
            {(byType.get(t) || []).map((m) => (
              <div key={m.id} className="tr">
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

function SkillsView({ skills, prompts, unifiedIntegrations, unifiedProxy, itemsRecent, onRunAction }) {
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

  const [ollamaModels, setOllamaModels] = useState([])
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

  const unifiedOk = Boolean(unifiedIntegrations?.ok)
  const unifiedData = unifiedIntegrations?.data
  const openapi = unifiedData?.openapi
  const openapiPaths = Array.isArray(openapi?.paths_sample) ? openapi.paths_sample : []
  const supportsPath = (p) => {
    const s = String(p || '')
    if (!s) return false
    if (openapiPaths.includes(s)) return true
    // OpenAPIが /api と非/api の両方を持つことがある
    if (s.startsWith('/api/') && openapiPaths.includes(s.replace('/api/', '/'))) return true
    if (s.startsWith('/') && openapiPaths.includes('/api' + s)) return true
    return false
  }

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
    try {
      const routes = {
        comfyui_queue: '/api/unified/comfyui/queue',
        comfyui_history: '/api/unified/comfyui/history',
        svi_queue: '/api/unified/svi/queue',
        svi_history: '/api/unified/svi/history',
        ltx2_queue: '/api/unified/ltx2/queue',
        ltx2_history: '/api/unified/ltx2/history',
        images_recent: '/api/unified/images/recent?limit=30',
        llm_health: '/api/unified/llm/health',
        llm_models: '/api/unified/llm/models-enhanced',
        unified_openapi: '/api/unified/openapi',
        unified_proxy_doctor: '/api/unified/proxy/doctor?limit=200&probe_timeout_s=1.5&max_total_s=8'
      }
      const path = routes[String(which)]
      if (!path) {
        setMonitorOut('ERR: unknown route')
        return
      }
      const r = await fetchJson(path)
      const text = JSON.stringify(r, null, 2)
      setMonitorOut(text.length > 18000 ? (text.slice(0, 18000) + '\n... (truncated)') : text)
    } catch (e) {
      setMonitorOut(`ERR: ${String(e?.message || e)}`)
    }
  }

  async function runMemoryRecall() {
    setMemoryOut('')
    try {
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
    }
  }

  async function runNotifySend() {
    setNotifyOut('')
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

      const base = getApiBase()
      const res = await fetch(`${base}/api/unified/notify/send`, {
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
    }
  }

  async function runNotifyJob() {
    setNotifyOut('')
    try {
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
    }
  }

  async function runMemoryStore() {
    setMemoryStoreOut('')
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

      const base = getApiBase()
      const res = await fetch(`${base}/api/unified/memory/store`, {
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
    }
  }

  async function runRouteEnhanced() {
    setRouteOut('')
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

      const base = getApiBase()
      const res = await fetch(`${base}/api/unified/llm/route-enhanced`, {
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
    }
  }

  async function runLlmAnalyze() {
    setAnalyzeOut('')
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

      const base = getApiBase()
      const res = await fetch(`${base}/api/unified/llm/analyze`, {
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
    }
  }

  async function runUnifiedProxy() {
    setProxyOut('')
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

      const base = getApiBase()
      const res = await fetch(`${base}/api/unified/proxy/run`, {
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
    try {
      const base = getApiBase()
      let payload = {}
      try {
        payload = videoBody && videoBody.trim() ? JSON.parse(videoBody) : {}
      } catch {
        setVideoOut('ERR: JSONが壊れてる')
        return
      }

      const res = await fetch(`${base}${videoEndpoint}`, {
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
    }
  }

  useEffect(() => {
    fetchJson('/api/ollama/tags')
      .then((r) => {
        const models = (r?.data?.models || []).map((m) => m?.name).filter(Boolean)
        setOllamaModels(models)
        if (!ollamaModel && models.length) setOllamaModel(models[0])
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function runOllama() {
    setOllamaOut('')
    const base = getApiBase()
    const res = await fetch(`${base}/api/ollama/generate`, {
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
  }

  async function queueImage() {
    setImgResult('')
    const base = getApiBase()
    const res = await fetch(`${base}/api/generate/image`, {
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
            <div className="tr th">
              <div>CATEGORY</div><div>TOOL</div><div>TYPE</div><div>AVAILABLE</div><div>KEY</div>
            </div>
            {toolRows.map((r, i) => (
              <div key={i} className="tr">
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
          {ollamaTemplates.length ? (
            <div className="kv"><span>TEMPLATE</span>
              <span>
                <select value={ollamaTpl} onChange={(e) => setOllamaTpl(e.target.value)}>
                  <option value="">(select)</option>
                  {ollamaTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link" style={{ marginLeft: 8 }} onClick={applyOllamaTemplate} disabled={!ollamaTpl}>適用</button>
              </span>
            </div>
          ) : null}
          <div className="kv"><span>MODEL</span>
            <span>
              <select value={ollamaModel} onChange={(e) => setOllamaModel(e.target.value)}>
                {ollamaModels.length ? ollamaModels.map((m) => <option key={m} value={m}>{m}</option>) : <option value="">(no models)</option>}
              </select>
            </span>
          </div>
          <textarea className="input" rows={4} value={ollamaPrompt} onChange={(e) => setOllamaPrompt(e.target.value)} placeholder="ここに質問や指示（例：要約して、案を出して、など）" />
          <div className="skillActions">
            <button className="link" onClick={runOllama} disabled={!ollamaModel || !ollamaPrompt.trim()}>実行</button>
          </div>
          {ollamaOut ? <pre className="output">{ollamaOut}</pre> : <div className="small">結果はここに出る（OpenWebUIも併用OK）</div>}
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
                <select value={imgTpl} onChange={(e) => setImgTpl(e.target.value)}>
                  <option value="">(select)</option>
                  {imageTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link" style={{ marginLeft: 8 }} onClick={applyImageTemplate} disabled={!imgTpl}>適用</button>
              </span>
            </div>
          ) : null}
          <textarea className="input" rows={3} value={imgPrompt} onChange={(e) => setImgPrompt(e.target.value)} placeholder="画像プロンプト（例：a cozy room, cinematic light, masterpiece）" />
          <textarea className="input" rows={2} value={imgNegative} onChange={(e) => setImgNegative(e.target.value)} placeholder="ネガティブ（任意）" />
          <div className="skillActions">
            <button className="link" onClick={queueImage} disabled={!imgPrompt.trim()}>キュー投入</button>
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
            <button className="link" onClick={() => fetchMonitor('comfyui_queue')}>ComfyUI queue</button>
            <button className="link" onClick={() => fetchMonitor('comfyui_history')}>ComfyUI history</button>
            <button className="link" onClick={() => fetchMonitor('svi_queue')}>SVI queue</button>
            <button className="link" onClick={() => fetchMonitor('svi_history')}>SVI history</button>
            <button className="link" onClick={() => fetchMonitor('ltx2_queue')}>LTX2 queue</button>
            <button className="link" onClick={() => fetchMonitor('ltx2_history')}>LTX2 history</button>
            <button className="link" onClick={() => fetchMonitor('images_recent')}>images recent</button>
            <button className="link" onClick={() => fetchMonitor('llm_health')}>LLM health</button>
            <button className="link" onClick={() => fetchMonitor('llm_models')}>LLM models</button>
            <button className="link" onClick={() => fetchMonitor('unified_openapi')}>Unified OpenAPI</button>
            <button className="link" onClick={() => fetchMonitor('unified_proxy_doctor')}>Proxy Doctor</button>
            <span className="small">AUTH? が出る場合は `MANAOS_UNIFIED_API_KEY` を設定</span>
          </div>
          {monitorOut ? <pre className="output">{monitorOut}</pre> : <div className="small">ここにJSONを表示（エラーも含む）</div>}
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
                  <select value={proxyId} onChange={(e) => setProxyId(e.target.value)}>
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
                  <span className="mono" style={{ marginLeft: 8 }}>{String(proxyRule.path || '')}</span>
                  <span className={String(proxyRule.gate || 'read') === 'danger' ? 'danger' : 'small'} style={{ marginLeft: 8 }}>
                    gate={String(proxyRule.gate || 'read')}
                  </span>
                  {proxyRule.enabled === false ? <span className="danger" style={{ marginLeft: 8 }}>DISABLED</span> : null}
                </div>
              ) : null}

              <textarea
                className="input"
                rows={3}
                value={proxyQuery}
                onChange={(e) => setProxyQuery(e.target.value)}
                placeholder={'query（任意・JSON） 例: {"limit":30} / path params は {"job_id":"..."} で渡す'}
              />
              {proxyRule && String(proxyRule.method || '').toUpperCase() === 'POST' ? (
                <textarea className="input" rows={4} value={proxyBody} onChange={(e) => setProxyBody(e.target.value)} placeholder="body（任意・JSON）" />
              ) : null}

              <div className="skillActions">
                <button className="link" onClick={runUnifiedProxy} disabled={!proxyId.trim() || !proxyRuleEnabled}>実行</button>
                <span className="small">write/danger は backend の環境変数ゲートが必要</span>
              </div>
              {proxyOut ? <pre className="output">{proxyOut}</pre> : <div className="small">結果はここに出る（ok/status/data/error）</div>}
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
            Memory: {' '}
            {unifiedOk && unifiedData?.memory_unified ? (
              unifiedData.memory_unified.available ? <span className="ok">AVAILABLE</span> : <span className="danger">UNAVAILABLE</span>
            ) : (
              <span className={unifiedOk ? 'small' : 'caution'}>{unifiedOk ? '—' : 'AUTH?'}</span>
            )}
            {' / '}Notification Hub: {' '}
            {unifiedOk && unifiedData?.notification_hub ? (
              unifiedData.notification_hub.available ? <span className="ok">AVAILABLE</span> : <span className="danger">UNAVAILABLE</span>
            ) : (
              <span className={unifiedOk ? 'small' : 'caution'}>{unifiedOk ? '—' : 'AUTH?'}</span>
            )}
          </div>

          <div className="kv" style={{ marginTop: 10 }}><span>QUERY</span>
            <span>
              <input className="input" value={memoryQuery} onChange={(e) => setMemoryQuery(e.target.value)} placeholder="memory recall query（必須）" />
            </span>
          </div>
          <div className="kv"><span>SCOPE</span>
            <span>
              <select value={memoryScope} onChange={(e) => setMemoryScope(e.target.value)}>
                <option value="all">all</option>
                <option value="short">short</option>
                <option value="long">long</option>
              </select>
            </span>
          </div>
          <div className="kv"><span>LIMIT</span>
            <span>
              <input className="input" type="number" min={1} max={50} value={memoryLimit} onChange={(e) => setMemoryLimit(e.target.value)} style={{ width: 120 }} />
            </span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runMemoryRecall} disabled={!memoryQuery.trim()}>recall（GET）</button>
            <span className="small">※ Unified APIの認証が必要（KEY未設定だとAUTH?）</span>
          </div>
          {memoryOut ? <pre className="output">{memoryOut}</pre> : <div className="small">結果はここに出る</div>}

          <div className="hr" style={{ margin: '14px 0' }} />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">MEMORY</span>
            <span>保存（POST）</span>
            <span className="small">/api/unified/memory/store</span>
          </div>
          <textarea className="input" rows={3} value={memoryStoreContent} onChange={(e) => setMemoryStoreContent(e.target.value)} placeholder="content（必須）" />
          <div className="kv"><span>FORMAT</span>
            <span>
              <select value={memoryStoreFormat} onChange={(e) => setMemoryStoreFormat(e.target.value)}>
                <option value="auto">auto</option>
                <option value="memo">memo</option>
                <option value="conversation">conversation</option>
                <option value="note">note</option>
              </select>
            </span>
          </div>
          <textarea className="input" rows={3} value={memoryStoreMeta} onChange={(e) => setMemoryStoreMeta(e.target.value)} placeholder="metadata（任意・JSON）" />
          <div className="skillActions">
            <button className="link" onClick={runMemoryStore} disabled={!memoryStoreContent.trim()}>保存（POST）</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {memoryStoreOut ? <pre className="output">{memoryStoreOut}</pre> : <div className="small">結果はここに出る（memory_id）</div>}

          <div className="hr" style={{ margin: '14px 0' }} />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">NOTIFY</span>
            <span>通知送信（POST）</span>
            <span className="small">/api/unified/notify/send</span>
          </div>

          <textarea className="input" rows={3} value={notifyMsg} onChange={(e) => setNotifyMsg(e.target.value)} placeholder="通知メッセージ（必須）" />
          <div className="kv"><span>PRIORITY</span>
            <span>
              <select value={notifyPriority} onChange={(e) => setNotifyPriority(e.target.value)}>
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </span>
          </div>
          <div className="kv"><span>ASYNC</span>
            <span>
              <select value={notifyAsync ? '1' : '0'} onChange={(e) => setNotifyAsync(e.target.value === '1')}>
                <option value="1">true（queued）</option>
                <option value="0">false（sync）</option>
              </select>
            </span>
          </div>

          <div className="skillActions">
            <button className="link" onClick={runNotifySend} disabled={!notifyMsg.trim()}>送信（POST）</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>

          <div className="kv"><span>JOB ID</span>
            <span>
              <input className="input" value={notifyJobId} onChange={(e) => setNotifyJobId(e.target.value)} placeholder="notifyjob_..." />
            </span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runNotifyJob} disabled={!notifyJobId.trim()}>ジョブ確認（GET）</button>
          </div>

          {notifyOut ? <pre className="output">{notifyOut}</pre> : <div className="small">結果はここに出る（queued/sent/failed など）</div>}
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
          <textarea className="input" rows={3} value={routePrompt} onChange={(e) => setRoutePrompt(e.target.value)} placeholder="prompt（必須）" />
          <textarea className="input" rows={3} value={routeCodeContext} onChange={(e) => setRouteCodeContext(e.target.value)} placeholder="code_context（任意・そのまま文字列）" />
          <textarea className="input" rows={4} value={routeContext} onChange={(e) => setRouteContext(e.target.value)} placeholder="context（任意・JSON）" />
          <textarea className="input" rows={4} value={routePrefs} onChange={(e) => setRoutePrefs(e.target.value)} placeholder="preferences（任意・JSON）" />
          <div className="skillActions">
            <button className="link" onClick={runRouteEnhanced} disabled={!routePrompt.trim()}>実行（POST）</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {routeOut ? <pre className="output">{routeOut}</pre> : <div className="small">結果はここに出る（選ばれたモデル/ルート/理由など）</div>}

          <div className="hr" style={{ margin: '14px 0' }} />

          <div className="sectionHead" style={{ marginTop: 0 }}>
            <span className="mono">ANALYZE</span>
            <span>難易度分析（POST）</span>
            <span className="small">/api/unified/llm/analyze</span>
          </div>
          <textarea className="input" rows={3} value={analyzePrompt} onChange={(e) => setAnalyzePrompt(e.target.value)} placeholder="prompt（必須）" />
          <textarea className="input" rows={3} value={analyzeCodeContext} onChange={(e) => setAnalyzeCodeContext(e.target.value)} placeholder="code_context（任意・そのまま文字列）" />
          <textarea className="input" rows={3} value={analyzeContext} onChange={(e) => setAnalyzeContext(e.target.value)} placeholder="context（任意・JSON）" />
          <div className="skillActions">
            <button className="link" onClick={runLlmAnalyze} disabled={!analyzePrompt.trim()}>分析（POST）</button>
          </div>
          {analyzeOut ? <pre className="output">{analyzeOut}</pre> : <div className="small">difficulty_score / level / recommended_model が出る</div>}
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
                <select value={videoTpl} onChange={(e) => setVideoTpl(e.target.value)}>
                  <option value="">(select)</option>
                  {videoTemplates.map((t) => <option key={t.id} value={t.id}>{t.label || t.id}</option>)}
                </select>
                <button className="link" style={{ marginLeft: 8 }} onClick={applyVideoTemplate} disabled={!videoTpl}>適用</button>
              </span>
            </div>
          ) : null}

          <div className="kv"><span>ENDPOINT</span>
            <span>
              <select value={videoEndpoint} onChange={(e) => setVideoEndpoint(e.target.value)}>
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
                <select value={pickRel} onChange={(e) => setPickRel(e.target.value)}>
                  <option value="">(recent images/videos)</option>
                  {mediaRecent.map((x, i) => {
                    const v = `${x.root_id}|${x.rel_path}`
                    const label = `${x.ext?.toUpperCase?.() || x.ext} / ${x.root_id}/${x.rel_path}`
                    return <option key={i} value={v}>{label}</option>
                  })}
                </select>
                <button className="link" style={{ marginLeft: 8 }} onClick={() => tryInsertPathField('start_image_path')} disabled={!pickRel}>start_imageへ</button>
                <button className="link" style={{ marginLeft: 8 }} onClick={() => tryInsertPathField('previous_video_path')} disabled={!pickRel}>prev_videoへ</button>
              </span>
            </div>
          ) : (
            <div className="small">recent items が空：先に何か生成/保存して「アイテム🎒」に出す</div>
          )}

          <textarea className="input" rows={8} value={videoBody} onChange={(e) => setVideoBody(e.target.value)} placeholder="ここにJSONボディ（テンプレ適用→編集）" />
          <div className="skillActions">
            <button className="link" onClick={runVideo} disabled={!videoEndpoint}>実行（POST）</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>
          {videoOut ? <pre className="output">{videoOut}</pre> : <div className="small">結果はここに出る（prompt_id / success / error）</div>}
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
                          <button className="link" onClick={() => onRunAction?.(it.action_id)}>実行</button>
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

function SystemsView({ unified }) {
  const base = unified?.base
  const r = unified?.integrations
  const ok = Boolean(r?.ok)
  const data = r?.data && typeof r.data === 'object' ? r.data : null

  const health = data?.health && typeof data.health === 'object' ? data.health : null
  const openapi = data?.openapi && typeof data.openapi === 'object' ? data.openapi : null

  const rows = data ? Object.entries(data).map(([k, v]) => ({
    key: k,
    name: v?.name,
    available: Boolean(v?.available),
    reason: v?.reason
  })) : []

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

      {rows.length && !health && !openapi ? (
        <div className="table" style={{ marginTop: 10 }}>
          <div className="tr th">
            <div>KEY</div><div>NAME</div><div>AVAILABLE</div><div>REASON</div>
          </div>
          {rows.map((x) => (
            <div key={x.key} className="tr">
              <div className="mono">{x.key}</div>
              <div>{x.name || '—'}</div>
              <div className={x.available ? 'ok' : 'danger'}>{x.available ? 'YES' : 'NO'}</div>
              <div className="small">{x.reason || '—'}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="small">データなし（APIキー未設定/認証NG の可能性）</div>
      )}
      <div className="small">必要なら環境変数で <span className="mono">MANAOS_UNIFIED_API_KEY</span>（または <span className="mono">MANAOS_INTEGRATION_READONLY_API_KEY</span>）をRPG backend側に渡す</div>
    </div>
  )
}

function QuestsView({ quests, apiBase, onRunAction, actionResult }) {
  const list = Array.isArray(quests) ? quests : []
  return (
    <div>
      <div className="panelTitle">クエスト（タスク）</div>
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
        <div className="tr th">
          <div>ID</div><div>LABEL</div><div>KIND</div><div>ENDPOINT</div><div>ACTION</div>
        </div>
        {list.map((q) => (
          <div key={q.id} className="tr">
            <div className="mono">{q.id}</div>
            <div>{q.label}</div>
            <div className="mono">{q.kind}</div>
            <div className="mono">{q.endpoint ?? q.action_id ?? '—'}</div>
            <div>
              {q.kind === 'api' && q.endpoint ? (
                <a className="link" href={`${apiBase}${q.endpoint}`} target="_blank" rel="noreferrer">実行</a>
              ) : q.kind === 'action' && q.action_id ? (
                <button className="link" onClick={() => onRunAction?.(q.action_id)}>実行</button>
              ) : (
                <span className="small">—</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function LogsView({ events }) {
  const list = Array.isArray(events) ? events : []
  return (
    <div>
      <div className="panelTitle">戦闘ログ</div>
      <div className="log">
        {list.length === 0 ? (
          <div className="small">events.log がまだ空です（サービスダウン等で自動追記）</div>
        ) : (
          list.slice().reverse().map((e, idx) => (
            <div key={idx} className="logLine">
              <span className="mono">{fmtTs(e.ts)}</span>
              <span className="mono">[{e.type}]</span>
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
  return (
    <div>
      <div className="panelTitle">マップ（デバイス）</div>
      <div className="table">
        <div className="tr th">
          <div>ID</div><div>NAME</div><div>KIND</div><div>TAGS</div>
        </div>
        {list.map((d) => (
          <div key={d.id} className="tr">
            <div className="mono">{d.id}</div>
            <div>{d.name}</div>
            <div className="mono">{d.kind}</div>
            <div className="small">{Array.isArray(d.tags) ? d.tags.join(', ') : '—'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function encodeRelPath(relPath) {
  const p = String(relPath || '').replace(/\\/g, '/')
  return p.split('/').map(encodeURIComponent).join('/')
}

function fmtBytes(n) {
  const v = Number(n || 0)
  if (!Number.isFinite(v) || v <= 0) return '0B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let x = v
  let i = 0
  while (x >= 1024 && i < units.length - 1) {
    x /= 1024
    i++
  }
  return `${x.toFixed(i === 0 ? 0 : 1)}${units[i]}`
}

function ItemsView({ items, apiBase }) {
  const recent = Array.isArray(items?.recent) ? items.recent : []
  const roots = Array.isArray(items?.roots) ? items.roots : []

  const labelById = new Map(roots.map((r) => [r.id, r.label]))
  const grouped = new Map()
  for (const it of recent) {
    const rid = String(it?.root_id || 'unknown')
    if (!grouped.has(rid)) grouped.set(rid, [])
    grouped.get(rid).push(it)
  }

  const groupKeys = Array.from(grouped.keys()).sort((a, b) => {
    const la = labelById.get(a) || a
    const lb = labelById.get(b) || b
    return String(la).localeCompare(String(lb))
  })

  return (
    <div>
      <div className="panelTitle">アイテム（生成物）</div>
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
                {(grouped.get(rid) || []).slice(0, 24).map((it, idx) => {
                  const url = `${apiBase}/files/${encodeURIComponent(it.root_id)}/${encodeRelPath(it.rel_path)}`
                  return (
                    <div key={`${it.root_id}:${it.rel_path}:${idx}`} className="itemCard">
                      <div className="itemHead">
                        <div className="mono">{it.kind}</div>
                        <div className="small">{fmtTs(it.mtime)} / {fmtBytes(it.size_bytes)}</div>
                      </div>
                      <div className="itemBody">
                        {it.kind === 'image' ? (
                          <a href={url} target="_blank" rel="noreferrer" className="itemMedia">
                            <img src={url} alt={it.name} loading="lazy" />
                          </a>
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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
