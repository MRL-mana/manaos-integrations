import { memo, useEffect, useMemo, useState } from 'react'
import { fmtBytes, dangerRank } from '../utils.js'
import { fetchJson } from '../api.js'
import Box from './Box.jsx'
import OutputBlock from './OutputBlock.jsx'
import DashboardConfig from './DashboardConfig.jsx'

function fmtAgeSec(v) {
  const n = Number(v)
  if (!Number.isFinite(n) || n < 0) return '—'
  if (n < 60) return `${Math.floor(n)}秒前`
  if (n < 3600) return `${Math.floor(n / 60)}分前`
  return `${Math.floor(n / 3600)}時間前`
}

function successRateClass(rate) {
  const n = Number(rate)
  if (!Number.isFinite(n)) return 'mono'
  if (n >= 95) return 'ok'
  if (n >= 80) return 'caution'
  return 'danger'
}

function overallLevelClass(level) {
  if (level === 'OK') return 'ok'
  if (level === 'WATCH') return 'caution'
  if (level === 'ALERT') return 'danger'
  return 'mono'
}

function overallReasonLabel(reason) {
  if (reason === 'all_green') return '全系統正常（成功率しきい値クリア）'
  if (reason === 'component_down') return '構成要素のいずれかが異常'
  if (reason === 'no_history_data') return '履歴データ不足（判定保留）'
  if (reason === 'success_rate_caution') return '成功率が注意域（80%以上95%未満）'
  if (reason === 'success_rate_low') return '成功率が警戒域（80%未満）'
  return reason || '—'
}

const GaugeBar = memo(function GaugeBar({ label, pct }) {
  const p = Math.max(0, Math.min(100, Number(pct || 0)))
  const cls = p >= 90 ? 'gaugeDanger' : p >= 70 ? 'gaugeCaution' : 'gaugeOk'
  return (
    <div className="gaugeWrap" role="progressbar" aria-valuenow={p} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="gaugeTrack">
        <div className={`gaugeFill ${cls}`} style={{ width: `${p}%` }} />
      </div>
      <div className="gaugeLabel">
        <span>{label}</span>
        <span className={`mono ${cls === 'gaugeDanger' ? 'danger' : cls === 'gaugeCaution' ? 'caution' : ''}`}>{p.toFixed(0)}%</span>
      </div>
    </div>
  )
})

export default function StatusView({ host, storage, google, services, models, devices, skills, danger, rlAnything, autonomy, nextActions, nextActionHints, onRunAction, actionResult, actionsEnabled, runningAction, lessons, agents }) {
  const [showConfig, setShowConfig] = useState(false)
  const [manualCheck, setManualCheck] = useState(null)
  const [manualSaving, setManualSaving] = useState(false)
  const [manualMsg, setManualMsg] = useState('')
  const [taskActionMsg, setTaskActionMsg] = useState('')
  const [taskActionBusyId, setTaskActionBusyId] = useState('')
  const [completedTaskIds, setCompletedTaskIds] = useState(() => new Set())
  const [taskCreateTitle, setTaskCreateTitle] = useState('')
  const [taskCreateBusy, setTaskCreateBusy] = useState(false)
  const [taskCreateMsg, setTaskCreateMsg] = useState('')
  const [calendarCreateTitle, setCalendarCreateTitle] = useState('')
  const [calendarCreateBusy, setCalendarCreateBusy] = useState(false)
  const [calendarCreateMsg, setCalendarCreateMsg] = useState('')
  const [calendarDeleteBusyId, setCalendarDeleteBusyId] = useState('')
  const [calendarDeleteMsg, setCalendarDeleteMsg] = useState('')
  const [deletedCalendarEventIds, setDeletedCalendarEventIds] = useState(() => new Set())
  const [gmailActionMsg, setGmailActionMsg] = useState('')
  const [gmailActionBusyId, setGmailActionBusyId] = useState('')
  const [readMailIds, setReadMailIds] = useState(() => new Set())
  const cpu = host?.cpu?.percent
  const mem = host?.mem?.percent
  const diskFree = host?.disk?.free_gb
  const diskTotal = host?.disk?.total_gb
  const hostname = host?.host?.hostname
  const os = host?.host?.os
  const diskRoot = host?.host?.disk_root
  const diskList = Array.isArray(host?.disks) ? host.disks : []
  const diskListSorted = useMemo(() => {
    return [...diskList].sort((a, b) => {
      const ap = Number(a?.used_percent)
      const bp = Number(b?.used_percent)
      const av = Number.isFinite(ap) ? ap : -1
      const bv = Number.isFinite(bp) ? bp : -1
      return bv - av
    })
  }, [diskList])
  const storageDisk = storage?.disk || {}
  const storageRoots = Array.isArray(storage?.item_roots) ? storage.item_roots : []
  const googleFiles = google?.files || {}
  const googleServices = google?.services || {}
  const googleCapabilities = Array.isArray(google?.capabilities) ? google.capabilities : []
  const googleSummary = google?.capabilities_summary || {}
  const googleToken = google?.token || {}
  const googleNextSteps = Array.isArray(google?.next_steps) ? google.next_steps : []
  const googleLive = google?.live_preview || {}
  const drivePreview = googleLive?.drive_files || {}
  const gmailPreview = googleLive?.gmail_profile || {}
  const calendarPreview = googleLive?.calendar_events || {}
  const tasksPreview = googleLive?.tasks_open || {}
  const visibleCalendarEvents = useMemo(() => {
    const base = Array.isArray(calendarPreview?.events) ? calendarPreview.events : []
    return base.filter((e) => !deletedCalendarEventIds.has(String(e?.id || '')))
  }, [calendarPreview, deletedCalendarEventIds])
  const gmailUnread = Array.isArray(gmailPreview?.unread_messages) ? gmailPreview.unread_messages : []
  const gmailCanMarkRead = gmailPreview?.can_mark_read === true
  const visibleUnreadMails = useMemo(() => {
    return gmailUnread.filter((m) => !readMailIds.has(String(m?.id || '')))
  }, [gmailUnread, readMailIds])
  const visibleTasks = useMemo(() => {
    const base = Array.isArray(tasksPreview?.tasks) ? tasksPreview.tasks : []
    return base.filter((t) => !completedTaskIds.has(String(t?.id || '')))
  }, [tasksPreview, completedTaskIds])

  const nvidia = Array.isArray(host?.gpu?.nvidia) ? host.gpu.nvidia : []
  const apps = Array.isArray(host?.gpu?.apps) ? host.gpu.apps : []

  const hints = useMemo(() => (Array.isArray(nextActionHints) ? nextActionHints : []), [nextActionHints])
  const actions = useMemo(() => (Array.isArray(nextActions) ? nextActions : []), [nextActions])

  const svcList = useMemo(() => (Array.isArray(services) ? services : []), [services])
  const svcAlive = useMemo(() => svcList.filter(s => s.alive).length, [svcList])
  const svcDown = svcList.length - svcAlive

  const chain = autonomy?.rpg_health_chain || {}
  const scheduler = autonomy?.scheduler || {}
  const unifiedLlm = autonomy?.unified_llm || {}
  const overall = autonomy?.overall || {}
  const overallLevel = overall.level || (overall.ok ? 'OK' : 'ALERT')
  const overallReason = overall.reason
  const historyStats = autonomy?.history_stats || {}

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

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const data = await fetchJson('/api/manual-check')
        if (mounted) {
          setManualCheck(data)
          setManualMsg('')
        }
      } catch (e) {
        if (mounted) setManualMsg(`manual-check 読み込み失敗: ${e?.message || e}`)
      }
    })()
    return () => { mounted = false }
  }, [])

  async function saveManualCheck(nextData) {
    setManualSaving(true)
    try {
      const res = await fetchJson('/api/manual-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextData || manualCheck || {}),
      })
      const saved = res?.manual_check || nextData
      setManualCheck(saved)
      setManualMsg(`保存済み (${saved?.completed?.count ?? 0}/${saved?.completed?.total ?? 7})`)
    } catch (e) {
      setManualMsg(`manual-check 保存失敗: ${e?.message || e}`)
    } finally {
      setManualSaving(false)
    }
  }

  function toggleManualItem(id) {
    if (!manualCheck?.checks) return
    const nextChecks = manualCheck.checks.map((item) => item.id === id ? { ...item, checked: !item.checked } : item)
    const count = nextChecks.filter((item) => item.checked).length
    const next = {
      ...manualCheck,
      checks: nextChecks,
      completed: {
        count,
        total: nextChecks.length,
        ok: count === nextChecks.length,
      },
    }
    setManualCheck(next)
  }

  function setManualField(key, value) {
    if (!manualCheck) return
    setManualCheck({ ...manualCheck, [key]: value })
  }

  async function completeGoogleTask(task) {
    const taskId = String(task?.id || '')
    const taskListId = String(task?.task_list_id || '')
    if (!taskId || !taskListId) {
      setTaskActionMsg('task id/list id が不足しています')
      return
    }
    setTaskActionBusyId(taskId)
    setTaskActionMsg('')
    try {
      const res = await fetchJson('/api/google/tasks/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, task_list_id: taskListId }),
      })
      if (!res?.ok) {
        throw new Error(res?.detail || res?.error || res?.reason || 'task complete failed')
      }
      setCompletedTaskIds((prev) => {
        const next = new Set(prev)
        next.add(taskId)
        return next
      })
      setTaskActionMsg(`完了: ${task?.title || taskId}`)
      await fetchJson('/api/snapshot?force=1').catch(() => {})
    } catch (e) {
      setTaskActionMsg(`完了処理失敗: ${e?.message || e}`)
    } finally {
      setTaskActionBusyId('')
    }
  }

  async function createGoogleTask() {
    const title = String(taskCreateTitle || '').trim()
    if (!title) {
      setTaskCreateMsg('タイトルを入力してください')
      return
    }
    setTaskCreateBusy(true)
    setTaskCreateMsg('')
    try {
      const res = await fetchJson('/api/google/tasks/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
      if (!res?.ok) {
        throw new Error(res?.detail || res?.error || res?.reason || 'task create failed')
      }
      setTaskCreateTitle('')
      setTaskCreateMsg(`追加: ${res?.task?.title || title}`)
      setCompletedTaskIds(() => new Set())
      await fetchJson('/api/snapshot?force=1').catch(() => {})
    } catch (e) {
      setTaskCreateMsg(`追加失敗: ${e?.message || e}`)
    } finally {
      setTaskCreateBusy(false)
    }
  }

  async function createCalendarEvent() {
    const summary = String(calendarCreateTitle || '').trim()
    if (!summary) {
      setCalendarCreateMsg('件名を入力してください')
      return
    }
    setCalendarCreateBusy(true)
    setCalendarCreateMsg('')
    try {
      const res = await fetchJson('/api/google/calendar/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary }),
      })
      if (!res?.ok) {
        throw new Error(res?.detail || res?.error || res?.reason || 'calendar create failed')
      }
      setCalendarCreateTitle('')
      setCalendarCreateMsg(`追加: ${res?.event?.summary || summary}`)
      setDeletedCalendarEventIds(() => new Set())
      await fetchJson('/api/snapshot?force=1').catch(() => {})
    } catch (e) {
      setCalendarCreateMsg(`追加失敗: ${e?.message || e}`)
    } finally {
      setCalendarCreateBusy(false)
    }
  }

  async function deleteCalendarEvent(event) {
    const eventId = String(event?.id || '')
    if (!eventId) {
      setCalendarDeleteMsg('event id が不足しています')
      return
    }
    setCalendarDeleteBusyId(eventId)
    setCalendarDeleteMsg('')
    try {
      const res = await fetchJson('/api/google/calendar/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId }),
      })
      if (!res?.ok) {
        throw new Error(res?.detail || res?.error || res?.reason || 'calendar delete failed')
      }
      setDeletedCalendarEventIds((prev) => {
        const next = new Set(prev)
        next.add(eventId)
        return next
      })
      setCalendarDeleteMsg(`削除: ${event?.summary || eventId}`)
      await fetchJson('/api/snapshot?force=1').catch(() => {})
    } catch (e) {
      setCalendarDeleteMsg(`削除失敗: ${e?.message || e}`)
    } finally {
      setCalendarDeleteBusyId('')
    }
  }

  async function markGmailRead(mail) {
    const messageId = String(mail?.id || '')
    if (!messageId) {
      setGmailActionMsg('message id が不足しています')
      return
    }
    setGmailActionBusyId(messageId)
    setGmailActionMsg('')
    try {
      const res = await fetchJson('/api/google/gmail/mark-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId }),
      })
      if (!res?.ok) {
        throw new Error(res?.detail || res?.error || res?.reason || 'gmail mark-read failed')
      }
      setReadMailIds((prev) => {
        const next = new Set(prev)
        next.add(messageId)
        return next
      })
      setGmailActionMsg(`既読: ${mail?.subject || messageId}`)
      await fetchJson('/api/snapshot?force=1').catch(() => {})
    } catch (e) {
      setGmailActionMsg(`既読処理失敗: ${e?.message || e}`)
    } finally {
      setGmailActionBusyId('')
    }
  }

  return (
    <div className="grid" style={{ position: 'relative' }}>
      {/* カスタマイズボタン */}
      <button
        className="settingsBtn"
        style={{ position: 'absolute', top: 8, right: 16, zIndex: 10 }}
        aria-label="ダッシュボードカスタマイズ"
        onClick={() => setShowConfig(true)}
      >🛠️ カスタマイズ</button>
      <Box title="母艦ステータス">
        <div className="kv"><span>HOST</span><span>{hostname || '—'}</span></div>
        <div className="kv"><span>OS</span><span className="mono">{os || '—'}</span></div>
      </Box>

      <Box title="CPU">
        <GaugeBar label="CPU" pct={cpu} />
      </Box>

      <Box title="RAM">
        <GaugeBar label="RAM" pct={mem} />
        <div className="small" style={{ marginTop: 4 }}>{host?.mem?.used_gb ?? '—'}GB / {host?.mem?.total_gb ?? '—'}GB</div>
      </Box>

      <Box title="DISK">
        {diskListSorted.length > 0 ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {diskListSorted.map((d, i) => {
              const total = Number(d?.total_gb || 0)
              const free = Number(d?.free_gb || 0)
              const pct = total > 0 ? ((total - free) / total) * 100 : 0
              const level = pct >= 90 ? 'ALERT' : pct >= 75 ? 'WATCH' : 'OK'
              const levelClass = pct >= 90 ? 'danger' : pct >= 75 ? 'caution' : 'ok'
              return (
                <div key={`${d?.root || 'disk'}-${i}`}>
                  <GaugeBar label={d?.root || `Disk${i + 1}`} pct={pct} />
                  <div className="small" style={{ marginTop: 4 }}>
                    free {d?.free_gb ?? '—'}GB / total {d?.total_gb ?? '—'}GB / <span className={levelClass}>{level}</span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <>
            <GaugeBar label={diskRoot || 'C:'} pct={diskTotal > 0 ? ((diskTotal - (diskFree ?? 0)) / diskTotal) * 100 : 0} />
            <div className="small" style={{ marginTop: 4 }}>free {diskFree ?? '—'}GB / total {diskTotal ?? '—'}GB</div>
          </>
        )}
      </Box>

      <Box title="ストレージ状態">
        <div className="kv"><span>対象root数</span><span className="mono">{storageRoots.length}</span></div>
        <div className="kv"><span>最近ファイル数</span><span className="mono">{storage?.recent_total_count ?? 0}</span></div>
        <div className="kv"><span>最近サイズ</span><span className="mono">{fmtBytes(storage?.recent_total_size_bytes)}</span></div>
        <div className="kv"><span>使用率</span><span className="mono">{typeof storageDisk?.used_percent === 'number' ? `${storageDisk.used_percent}%` : '—'}</span></div>
        <div className="small" style={{ marginTop: 6 }}>画像/動画の生成物rootサマリー</div>
        {storageRoots.length > 0 ? (
          <div style={{ marginTop: 8 }}>
            {storageRoots.slice(0, 8).map((root) => (
              <div key={root?.root_id || root?.label} className="kv">
                <span>{root?.label || root?.root_id}</span>
                <span className="mono">{root?.recent_count ?? 0}件 / {fmtBytes(root?.recent_size_bytes || 0)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </Box>

      <Box title="Googleサービス状態">
        <div className="kv"><span>Drive準備</span><span className={google?.drive_ready ? 'ok' : 'caution'}>{google?.drive_ready ? 'READY' : 'SETUP NEEDED'}</span></div>
        <div className="kv"><span>利用可能</span><span className="mono">{googleSummary?.usable ?? 0}/{googleSummary?.total ?? 0}</span></div>
        <div className="kv"><span>token</span><span className={googleToken?.has_access_token ? 'ok' : 'danger'}>{googleToken?.has_access_token ? 'OK' : 'MISSING'}</span></div>
        <div className="kv"><span>token expiry</span><span className={googleToken?.expired ? 'danger' : 'mono'}>{googleToken?.expiry || '—'}</span></div>
        <div className="kv"><span>credentials.json</span><span className={googleFiles?.credentials_json?.exists ? 'ok' : 'danger'}>{googleFiles?.credentials_json?.exists ? 'OK' : 'MISSING'}</span></div>
        <div className="kv"><span>token.json</span><span className={googleFiles?.token_json?.exists ? 'ok' : 'danger'}>{googleFiles?.token_json?.exists ? 'OK' : 'MISSING'}</span></div>
        <div className="kv"><span>sync config</span><span className={googleFiles?.google_drive_sync_config?.exists ? 'ok' : 'caution'}>{googleFiles?.google_drive_sync_config?.exists ? 'OK' : 'OPTIONAL'}</span></div>
        <div className="kv"><span>integration module</span><span className={googleServices?.integration_module?.exists ? 'ok' : 'danger'}>{googleServices?.integration_module?.exists ? 'OK' : 'MISSING'}</span></div>
        {googleCapabilities.length > 0 ? (
          <div style={{ marginTop: 8 }}>
            {googleCapabilities.map((cap) => {
              const usable = !!cap?.usable
              const reason = String(cap?.reason || '')
              let reasonLabel = 'ready'
              if (reason === 'auth_missing') reasonLabel = 'auth missing'
              else if (reason === 'module_missing') reasonLabel = 'module missing'
              else if (reason === 'scope_missing') reasonLabel = 'scope missing'
              else if (reason === 'scope_unknown') reasonLabel = 'scope unknown'
              return (
                <div key={cap?.id || cap?.label} className="kv">
                  <span>{cap?.label || cap?.id}</span>
                  <span className={usable ? 'ok' : 'caution'}>{usable ? 'USABLE' : `NOT READY (${reasonLabel})`}</span>
                </div>
              )
            })}
          </div>
        ) : null}

        <div className="small mono" style={{ marginTop: 10 }}>Driveファイル表示: {drivePreview?.ok ? 'ON' : `OFF (${drivePreview?.reason || 'not_ready'})`}</div>
        {drivePreview?.ok && Array.isArray(drivePreview?.files) ? (
          <div style={{ marginTop: 6 }}>
            {drivePreview.files.slice(0, 5).map((f) => (
              <div key={f?.id || f?.name} className="kv">
                <span>{f?.name || '—'}</span>
                <span className="mono">{f?.mimeType || '—'}</span>
              </div>
            ))}
          </div>
        ) : null}

        <div className="small mono" style={{ marginTop: 10 }}>Gmail表示: {gmailPreview?.ok ? 'ON' : `OFF (${gmailPreview?.reason || 'not_ready'})`}</div>
        {gmailPreview?.ok ? (
          <div style={{ marginTop: 6 }}>
            <div className="kv"><span>mailbox</span><span className="mono">{gmailPreview?.email || '—'}</span></div>
            <div className="kv"><span>messages</span><span className="mono">{gmailPreview?.messages_total ?? '—'}</span></div>
            <div className="kv"><span>threads</span><span className="mono">{gmailPreview?.threads_total ?? '—'}</span></div>
            {visibleUnreadMails.length > 0 ? (
              <div style={{ marginTop: 6 }}>
                {visibleUnreadMails.slice(0, 3).map((mail, idx) => (
                  <div key={mail?.id || idx} className="kv">
                    <span>{mail?.subject || '（件名なし）'}</span>
                    <span className="mono">{mail?.from || 'unknown'}</span>
                    <button className="link" disabled={!gmailCanMarkRead || gmailActionBusyId === String(mail?.id || '')} onClick={() => markGmailRead(mail)}>
                      {gmailActionBusyId === String(mail?.id || '') ? '既読中…' : '既読'}
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
            {!gmailCanMarkRead ? <div className="small mono" style={{ marginTop: 6 }}>既読操作には `gmail.modify` scope が必要です</div> : null}
            {gmailActionMsg ? <div className="small mono" style={{ marginTop: 6 }}>{gmailActionMsg}</div> : null}
          </div>
        ) : null}

        <div className="small mono" style={{ marginTop: 10 }}>Calendar表示: {calendarPreview?.ok ? 'ON' : `OFF (${calendarPreview?.reason || 'not_ready'})`}</div>
        <div style={{ marginTop: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
          <input
            type="text"
            value={calendarCreateTitle}
            onChange={(e) => setCalendarCreateTitle(e.target.value)}
            placeholder="新しい予定"
            disabled={calendarCreateBusy}
            style={{ flex: 1 }}
          />
          <button onClick={createCalendarEvent} disabled={calendarCreateBusy}>{calendarCreateBusy ? '追加中…' : '追加'}</button>
        </div>
        {calendarCreateMsg ? <div className="small mono" style={{ marginTop: 4 }}>{calendarCreateMsg}</div> : null}
        {calendarPreview?.ok && Array.isArray(visibleCalendarEvents) ? (
          <div style={{ marginTop: 6 }}>
            {visibleCalendarEvents.slice(0, 3).map((e) => (
              <div key={e?.id || e?.summary} className="kv">
                <span>{e?.summary || '（無題）'}</span>
                <span className="mono">{e?.start || '—'}</span>
                <button className="link" disabled={calendarDeleteBusyId === String(e?.id || '')} onClick={() => deleteCalendarEvent(e)}>
                  {calendarDeleteBusyId === String(e?.id || '') ? '削除中…' : '削除'}
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {calendarDeleteMsg ? <div className="small mono" style={{ marginTop: 4 }}>{calendarDeleteMsg}</div> : null}

        <div className="small mono" style={{ marginTop: 10 }}>TODO表示: {tasksPreview?.ok ? 'ON' : `OFF (${tasksPreview?.reason || 'not_ready'})`}</div>
        <div style={{ marginTop: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
          <input
            type="text"
            value={taskCreateTitle}
            onChange={(e) => setTaskCreateTitle(e.target.value)}
            placeholder="新しいTODO"
            disabled={taskCreateBusy}
            style={{ flex: 1 }}
          />
          <button onClick={createGoogleTask} disabled={taskCreateBusy}>{taskCreateBusy ? '追加中…' : '追加'}</button>
        </div>
        {taskCreateMsg ? <div className="small mono" style={{ marginTop: 4 }}>{taskCreateMsg}</div> : null}
        {tasksPreview?.ok && Array.isArray(visibleTasks) ? (
          <div style={{ marginTop: 6 }}>
            {visibleTasks.slice(0, 3).map((t) => (
              <div key={t?.id || t?.title} className="kv">
                <span>{t?.title || '（無題）'}</span>
                <span className="mono">{t?.due || '—'}</span>
                <button className="link" disabled={taskActionBusyId === String(t?.id || '')} onClick={() => completeGoogleTask(t)}>
                  {taskActionBusyId === String(t?.id || '') ? '完了中…' : '完了'}
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {taskActionMsg ? <div className="small mono" style={{ marginTop: 6 }}>{taskActionMsg}</div> : null}

        {googleNextSteps.length > 0 ? (
          <div style={{ marginTop: 10 }}>
            <div className="small mono" style={{ marginBottom: 4 }}>次の手順</div>
            {googleNextSteps.slice(0, 5).map((step, idx) => (
              <div key={`gstep-${idx}`} className="small">- {step}</div>
            ))}
          </div>
        ) : null}
      </Box>

      <Box title="GPU (NVIDIA)">
        {nvidia.length === 0 ? (
          <div className="small">nvidia-smi 未検出 / 取得不可</div>
        ) : (
          nvidia.map((g, i) => (
            <div key={i} className="gpuRow">
              <div className="mono">{g.name}</div>
              {typeof g.utilization_gpu === 'number' ? (
                <GaugeBar label="UTIL" pct={g.utilization_gpu} />
              ) : (
                <div className="small gpuDetail">UTIL —</div>
              )}
              {typeof g.mem_used_mb === 'number' && typeof g.mem_total_mb === 'number' && g.mem_total_mb > 0 ? (
                <div>
                  <GaugeBar label="VRAM" pct={(g.mem_used_mb / g.mem_total_mb) * 100} />
                  <div className="small" style={{ marginTop: 2 }}>{g.mem_used_mb}MB / {g.mem_total_mb}MB</div>
                </div>
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

      <Box title={`サービス稼働 ${svcAlive}/${svcList.length}`}>
        <div className="kv"><span>ALIVE</span><span className="ok">{svcAlive}</span></div>
        <div className="kv"><span>DOWN</span><span className={svcDown > 0 ? 'danger' : 'small'}>{svcDown}</span></div>
        <div className="healthMini">
          {svcList.map(s => (
            <div key={s.id}
                 className={`healthMiniDot ${s.alive ? 'healthMiniDotAlive' : 'healthMiniDotDead'}`}
                 title={`${s.name}: ${s.alive ? 'ALIVE' : 'DOWN'}`}
            />
          ))}
        </div>
      </Box>

      {/* ─── ダッシュボード統計 ─── */}
      <Box title="全体統計">
        <div className="dashStats">
          <div className="dashStat">
            <div className="dashStatValue">{Array.isArray(models) ? models.length : 0}</div>
            <div className="dashStatLabel">📚 モデル</div>
          </div>
          <div className="dashStat">
            <div className="dashStatValue">{Array.isArray(devices) ? devices.length : 0}</div>
            <div className="dashStatLabel">🧭 デバイス</div>
          </div>
          <div className="dashStat">
            <div className="dashStatValue">{Array.isArray(skills) ? skills.length : 0}</div>
            <div className="dashStatLabel">✨ スキル</div>
          </div>
          <div className="dashStat">
            <div className={`dashStatValue ${dangerRank(danger).cls}`}>{danger ?? 0}</div>
            <div className="dashStatLabel">⚠️ 危険度</div>
          </div>
        </div>
        {rlAnything?.enabled ? (
          <div className="kv" style={{ marginTop: 8 }}>
            <span>🧠 RL Cycle</span>
            <span className="mono">{rlAnything.cycle_count ?? 0} / {rlAnything.current_difficulty ?? '—'}</span>
          </div>
        ) : null}
      </Box>

      <Box title="自動運用モニタ">
        <div className="kv"><span>総合判定</span><span className={overallLevelClass(overallLevel)}>{overallLevel}</span></div>
        <div className="small mono" style={{ marginBottom: 6 }}>{overall.summary || 'status unavailable'}</div>
        <div className="kv"><span>総合理由</span><span className="mono">{overallReasonLabel(overallReason)}</span></div>

        <div className="kv"><span>RPGヘルスチェーン</span><span className={chain.ok ? 'ok' : 'danger'}>{chain.found ? (chain.ok ? 'PASS' : 'FAIL') : 'N/A'}</span></div>
        <div className="kv"><span>最終実行</span><span className="mono">{fmtAgeSec(chain.age_sec)}</span></div>
        <div className="kv"><span>失敗ステップ</span><span className={Number(chain.failed_step_count || 0) > 0 ? 'danger' : 'ok'}>{Number(chain.failed_step_count || 0)}</span></div>
        <div className="kv"><span>判定理由</span><span className="mono">{chain.ok_reason || '—'}</span></div>
        <div className="kv"><span>24h成功率</span><span className={`${successRateClass(historyStats.rate24h)} mono`}>{typeof historyStats.rate24h === 'number' ? `${historyStats.rate24h}% (${historyStats.ok24h}/${historyStats.count24h})` : '—'}</span></div>
        <div className="kv"><span>直近{historyStats.recent_window ?? 20}回成功率</span><span className={`${successRateClass(historyStats.rateRecent)} mono`}>{typeof historyStats.rateRecent === 'number' ? `${historyStats.rateRecent}% (${historyStats.okRecent}/${historyStats.countRecent})` : '—'}</span></div>

        <div className="kv" style={{ marginTop: 8 }}><span>スケジューラ</span><span className={scheduler.ok ? 'ok' : 'danger'}>{scheduler.found ? (scheduler.ok ? 'OK' : 'NG') : '未設定'}</span></div>
        <div className="kv"><span>タスク名</span><span className="mono">{scheduler.task_name || '—'}</span></div>
        <div className="kv"><span>間隔</span><span className="mono">{scheduler.interval_minutes ? `${scheduler.interval_minutes}分` : '—'}</span></div>
        <div className="small mono" style={{ marginBottom: 6 }}>{Array.isArray(scheduler.status_summary) && scheduler.status_summary.length > 0 ? scheduler.status_summary.join(' / ') : 'status_summary: —'}</div>

        <div className="kv" style={{ marginTop: 8 }}><span>Unified LLM</span><span className={unifiedLlm.ok ? 'ok' : 'danger'}>{unifiedLlm.ok ? 'ONLINE' : 'OFFLINE'}</span></div>
        <div className="kv"><span>Backend</span><span className="mono">{unifiedLlm.llm_server || '—'}</span></div>
        <div className="kv"><span>モデル数</span><span className="mono">{unifiedLlm.available_models ?? '—'}</span></div>
        <div className="kv"><span>Policy fail_closed</span><span className={typeof unifiedLlm.policy_fail_closed === 'boolean' ? (unifiedLlm.policy_fail_closed ? 'ok' : 'danger') : 'mono'}>{typeof unifiedLlm.policy_fail_closed === 'boolean' ? String(unifiedLlm.policy_fail_closed) : 'unknown'}</span></div>
      </Box>

      <Box title="manual=7 日次チェック">
        <div className="kv"><span>date</span><span className="mono">{manualCheck?.date || '—'}</span></div>
        <div className="kv"><span>mode</span><span className={manualCheck?.mode_expected === 'safe' ? 'ok' : 'caution'}>{manualCheck?.mode_expected || 'safe'}</span></div>
        <div className="kv"><span>完了</span><span className={(manualCheck?.completed?.ok ? 'ok' : 'caution') + ' mono'}>{manualCheck?.completed?.count ?? 0}/{manualCheck?.completed?.total ?? 7}</span></div>

        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
          <label className="small" style={{ display: 'grid', gap: 4 }}>
            <span className="mono">operator</span>
            <input
              type="text"
              value={manualCheck?.operator || ''}
              onChange={(e) => setManualField('operator', e.target.value)}
              disabled={manualSaving}
              placeholder="operator name"
            />
          </label>
          <label className="small" style={{ display: 'grid', gap: 4 }}>
            <span className="mono">run_id (optional)</span>
            <input
              type="text"
              value={manualCheck?.run_id || ''}
              onChange={(e) => setManualField('run_id', e.target.value)}
              disabled={manualSaving}
              placeholder="run id"
            />
          </label>
        </div>

        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
          {(manualCheck?.checks || []).map((item) => (
            <label key={item.id} className="small" style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={!!item.checked}
                onChange={() => toggleManualItem(item.id)}
                disabled={manualSaving}
              />
              <span className="mono" style={{ minWidth: 28 }}>{item.id}</span>
              <span>{item.title}</span>
            </label>
          ))}
        </div>

        <div style={{ marginTop: 10, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => saveManualCheck(manualCheck)} disabled={manualSaving || !manualCheck}>
            {manualSaving ? '保存中…' : '保存'}
          </button>
          {manualCheck?.completed?.ok ? <span className="ok small">運用OKスタンプ: READY</span> : <span className="caution small">未完了項目あり</span>}
        </div>
        {Array.isArray(manualCheck?.stamps_recent) && manualCheck.stamps_recent.length > 0 ? (
          <div style={{ marginTop: 10 }}>
            <div className="small mono" style={{ marginBottom: 4 }}>最近の完了スタンプ</div>
            {manualCheck.stamps_recent.slice(0, 5).map((stamp, idx) => (
              <div key={`${stamp?.stamp_id || 'stamp'}-${idx}`} className="small mono">
                - {stamp?.date || '—'} / {stamp?.operator || 'unknown'} / {stamp?.run_id || 'no-run-id'} / {stamp?.stamp_id || '—'}
              </div>
            ))}
          </div>
        ) : null}
        {manualMsg ? <div className="small mono" style={{ marginTop: 6 }}>{manualMsg}</div> : null}
      </Box>

      <Box title="次の一手" className="fullSpan">
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
          <div className="mt10">
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
      {/* AI成長ログ サマリー */}
      {(Number(lessons?.total) > 0 || Number(agents?.total_agents) > 0) ? (
        <Box title="📖 AI成長ログ">
          <div className="kv"><span>教訓</span><span className="mono">{lessons?.total ?? 0} 件</span></div>
          {lessons?.top_repeated?.[0] ? (
            <div className="small" style={{ color: '#aaa', marginTop: '2px' }}>最頼出: {String(lessons.top_repeated[0].instruction || '').slice(0, 60)}</div>
          ) : null}
          <div className="kv" style={{ marginTop: '6px' }}><span>エージェント</span><span className="mono">{agents?.total_agents ?? 0} 体</span></div>
          {Number(agents?.rank_distribution?.['N-S']) > 0 ? (
            <div className="small ok">★ N-S 達成: {agents.rank_distribution['N-S']} 体</div>
          ) : null}
          {Number(agents?.parking_candidates) > 0 ? (
            <div className="small caution">パーキング候補: {agents.parking_candidates} 体（30日未使用）</div>
          ) : null}
        </Box>
      ) : null}
      {/* DashboardConfig モーダル */}
      {showConfig && (
        <DashboardConfig onClose={() => setShowConfig(false)} />
      )}
    </div>
  )
}
