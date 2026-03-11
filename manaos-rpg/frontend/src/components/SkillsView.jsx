import { useState, useEffect, useMemo, useCallback } from 'react'
import { MONITOR_ROUTES, truncateOutput } from '../utils.js'
import { fetchJson } from '../api.js'
import OutputBlock from './OutputBlock.jsx'

export default function SkillsView({ skills, prompts, unifiedIntegrations, unifiedProxy, itemsRecent, apiBase, onRunAction, runningAction }) {
  const list = useMemo(() => (Array.isArray(skills) ? skills : []), [skills])
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
  }, [list, unifiedData, unifiedOk])

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

  const mediaRecent = useMemo(() => {
    const recent = Array.isArray(itemsRecent) ? itemsRecent : []
    const okExt = new Set(['png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'mkv', 'gif'])
    return recent
      .filter((x) => okExt.has(String(x?.ext || '').toLowerCase()))
      .slice(0, 40)
  }, [itemsRecent])
  const [pickRel, setPickRel] = useState('')

  function itemUriFromPick() {
    if (!pickRel) return ''
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

  const [gtdInbox, setGtdInbox] = useState([])
  const [gtdCaptureText, setGtdCaptureText] = useState('')
  const [gtdCaptureType, setGtdCaptureType] = useState('メモ')
  const [gtdCaptureNote, setGtdCaptureNote] = useState('')
  const [gtdMorning, setGtdMorning] = useState('')
  const [gtdProcessFile, setGtdProcessFile] = useState('')
  const [gtdProcessNA, setGtdProcessNA] = useState('')
  const [gtdOut, setGtdOut] = useState('')

  const proxyRules = useMemo(() => (Array.isArray(unifiedProxy?.rules) ? unifiedProxy.rules : []), [unifiedProxy])

  const openapi = unifiedIntegrations?.data?.openapi
  const openapiPathSet = useMemo(() => {
    const arr = Array.isArray(openapi?.paths_sample) ? openapi.paths_sample : []
    return new Set(arr)
  }, [openapi])
  const supportsPath = useCallback((p) => {
    const s = String(p || '')
    if (!s) return false
    if (openapiPathSet.has(s)) return true
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
      setMonitorOut(truncateOutput(text))
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
      setMemoryOut(truncateOutput(text))
    } catch (e) {
      setMemoryOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runNotifySend() {
    if (!window.confirm('通知を送信しますか？')) return
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
      setNotifyOut(truncateOutput(text))
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
      setNotifyOut(truncateOutput(text))
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
      setMemoryStoreOut(truncateOutput(text))
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
      setRouteOut(truncateOutput(text))
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
      setAnalyzeOut(truncateOutput(text))
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
      setProxyOut(truncateOutput(text))
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

  async function fetchGtdInbox() {
    setBusyOp('gtd_inbox')
    setGtdOut('')
    try {
      const res = await fetch(`${apiBase}/api/unified/gtd/inbox/list`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setGtdOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      setGtdInbox(Array.isArray(data?.data) ? data.data : [])
      setGtdOut(truncateOutput(JSON.stringify(data, null, 2)))
    } catch (e) {
      setGtdOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function fetchGtdMorning() {
    setBusyOp('gtd_morning')
    setGtdMorning('')
    setGtdOut('')
    try {
      const res = await fetch(`${apiBase}/api/unified/gtd/morning`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setGtdOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      const txt = data?.data?.summary || data?.data?.morning_summary || JSON.stringify(data.data, null, 2)
      setGtdMorning(truncateOutput(String(txt)))
      setGtdOut(truncateOutput(JSON.stringify(data, null, 2)))
    } catch (e) {
      setGtdOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runGtdCapture() {
    const text = gtdCaptureText.trim()
    if (!text) return
    setBusyOp('gtd_capture')
    setGtdOut('')
    try {
      const res = await fetch(`${apiBase}/api/unified/gtd/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, type: gtdCaptureType, note: gtdCaptureNote || undefined })
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setGtdOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      setGtdCaptureText('')
      setGtdCaptureNote('')
      setGtdOut(truncateOutput(JSON.stringify(data, null, 2)))
    } catch (e) {
      setGtdOut(`ERR: ${String(e?.message || e)}`)
    } finally {
      setBusyOp('')
    }
  }

  async function runGtdProcess() {
    const filename = gtdProcessFile.trim()
    if (!filename) return
    setBusyOp('gtd_process')
    setGtdOut('')
    try {
      const res = await fetch(`${apiBase}/api/unified/gtd/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, next_action: gtdProcessNA || undefined })
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.ok) {
        setGtdOut(`ERR: ${data?.detail || data?.error || res.status}`)
        return
      }
      setGtdProcessFile('')
      setGtdProcessNA('')
      setGtdOut(truncateOutput(JSON.stringify(data, null, 2)))
    } catch (e) {
      setGtdOut(`ERR: ${String(e?.message || e)}`)
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
          <div className="table mt10">
            <div className="tr th colsTools">
              <div>CATEGORY</div><div>TOOL</div><div>TYPE</div><div>AVAILABLE</div><div>KEY</div>
            </div>
            {toolRows.map((r, i) => (
              <div key={i} className={`tr colsTools${r.availability === 'NO' || r.availability === 'AUTH' ? ' trDanger' : ''}`}>
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
          {ollamaModelErr ? <div className="small danger mb6">{ollamaModelErr}</div> : null}
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
          <div className="skillActions">
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
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('gtd_status')}>GTD status</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('gtd_morning')}>GTD morning</button>
            <button className="link" disabled={!!busyOp} onClick={() => fetchMonitor('integrations_status')}>integrations status</button>
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

          <div className="kv mt10"><span>QUERY</span>
            <span>
              <input className="input" value={memoryQuery} onChange={(e) => setMemoryQuery(e.target.value)} placeholder="memory recall query（必須）" aria-label="メモリ検索クエリ" />
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
              <input className="input inputNarrow" type="number" min={1} max={50} value={memoryLimit} onChange={(e) => setMemoryLimit(Number(e.target.value) || 1)} aria-label="メモリ検索件数" />
            </span>
          </div>
          <div className="skillActions">
            <button className="link" onClick={runMemoryRecall} disabled={!!busyOp || !memoryQuery.trim()}>{busyOp === 'memory_recall' ? '検索中…' : 'recall（GET）'}</button>
            <span className="small">※ Unified APIの認証が必要（KEY未設定だとAUTH?）</span>
          </div>
          {memoryOut ? <OutputBlock text={memoryOut} onClear={() => setMemoryOut('')} /> : <div className="small">結果はここに出る</div>}

          <div className="hr" />

          <div className="sectionHead">
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

          <div className="sectionHead">
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
              <input className="input" value={notifyJobId} onChange={(e) => setNotifyJobId(e.target.value)} placeholder="notifyjob_..." aria-label="通知ジョブID" />
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
          <span className="mono">GTD</span>
          <span>タスク管理（Getting Things Done）</span>
          <span className="small">/api/unified/gtd/*</span>
        </div>
        <div className="boxBody">
          <div className="skillActions">
            <button className="link" disabled={!!busyOp} onClick={fetchGtdMorning}>{busyOp === 'gtd_morning' ? '…' : '今日の優先事項（morning）'}</button>
            <button className="link" disabled={!!busyOp} onClick={fetchGtdInbox}>{busyOp === 'gtd_inbox' ? '…' : 'Inbox 一覧'}</button>
          </div>
          {gtdMorning ? (
            <div className="small mt10" style={{ whiteSpace: 'pre-wrap', maxHeight: '180px', overflowY: 'auto' }}>{gtdMorning}</div>
          ) : null}
          {gtdInbox.length > 0 ? (
            <div className="mt10">
              <div className="small">Inbox（{gtdInbox.length}件）— クリックでファイル名を Process欄にセット</div>
              <div style={{ maxHeight: '140px', overflowY: 'auto' }}>
                {gtdInbox.map((f, i) => (
                  <div key={i} className="small mono" style={{ cursor: 'pointer', padding: '2px 0' }}
                    onClick={() => setGtdProcessFile(String(f?.filename || f || ''))}
                  >{String(f?.filename || f || '')}</div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="hr" />

          <div className="sectionHead">
            <span className="mono">CAPTURE</span>
            <span>Inbox に登録（POST）</span>
            <span className="small">/api/unified/gtd/capture</span>
          </div>
          <textarea className="input" rows={2} value={gtdCaptureText} onChange={(e) => setGtdCaptureText(e.target.value)} placeholder="text（必須）— 登録する内容" aria-label="GTDキャプチャテキスト" />
          <div className="kv">
            <span>TYPE</span>
            <span>
              <select value={gtdCaptureType} onChange={(e) => setGtdCaptureType(e.target.value)} aria-label="GTDキャプチャ種別">
                <option value="メモ">メモ</option>
                <option value="タスク">タスク</option>
                <option value="アイデア">アイデア</option>
                <option value="参照">参照</option>
                <option value="懸念">懸念</option>
              </select>
            </span>
          </div>
          <textarea className="input" rows={2} value={gtdCaptureNote} onChange={(e) => setGtdCaptureNote(e.target.value)} placeholder="note（任意）— 補足メモ" aria-label="GTDキャプチャノート" />
          <div className="skillActions">
            <button className="link" onClick={runGtdCapture} disabled={!!busyOp || !gtdCaptureText.trim()}>{busyOp === 'gtd_capture' ? '登録中…' : '登録（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>

          <div className="hr" />

          <div className="sectionHead">
            <span className="mono">PROCESS</span>
            <span>Inbox 処理（POST）</span>
            <span className="small">/api/unified/gtd/process</span>
          </div>
          <div className="kv">
            <span>FILE</span>
            <span>
              <input className="input" value={gtdProcessFile} onChange={(e) => setGtdProcessFile(e.target.value)} placeholder="filename（必須）— Inboxファイル名" aria-label="GTD処理ファイル名" />
            </span>
          </div>
          <textarea className="input" rows={2} value={gtdProcessNA} onChange={(e) => setGtdProcessNA(e.target.value)} placeholder="next_action（任意）— 次のアクション" aria-label="GTD次のアクション" />
          <div className="skillActions">
            <button className="link" onClick={runGtdProcess} disabled={!!busyOp || !gtdProcessFile.trim()}>{busyOp === 'gtd_process' ? '処理中…' : '処理（POST）'}</button>
            <span className="small">※ backendで `MANAOS_RPG_ENABLE_UNIFIED_WRITE=1` が必要</span>
          </div>

          {gtdOut ? <OutputBlock text={gtdOut} onClear={() => setGtdOut('')} /> : <div className="small">結果はここに出る</div>}
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

          <div className="sectionHead">
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
                          <span className="caution ml">AUTH?</span>
                        ) : null}
                        {it.integration_key && unifiedData?.[it.integration_key] ? (
                          <span className={`${unifiedData[it.integration_key]?.available ? 'ok' : 'danger'} ml`}>
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
