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
    } catch (e) {
      setErr(String(e?.message || e))
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
      const base = getApiBase()
      const res = await fetch(`${base}/api/actions/${encodeURIComponent(actionId)}/run`, {
        method: 'POST'
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`)
      }
      setActionResult(data)
      await refreshSnapshot()
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
    { id: 'items', label: 'アイテム（生成物）', icon: '🎒' }
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
          {active === 'status' ? <StatusView host={state?.host} nextActions={state?.next_actions} /> : null}
          {active === 'party' ? <PartyView services={state?.services} /> : null}
          {active === 'bestiary' ? <BestiaryView models={state?.models} /> : null}
          {active === 'skills' ? <SkillsView skills={state?.skills} /> : null}
          {active === 'quests' ? <QuestsView quests={state?.quests} apiBase={apiBase} onRunAction={runAction} actionResult={actionResult} /> : null}
          {active === 'logs' ? <LogsView events={events} /> : null}
          {active === 'map' ? <MapView devices={state?.devices} /> : null}
          {active === 'items' ? <ItemsView items={state?.items} apiBase={apiBase} /> : null}
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

function StatusView({ host, nextActions }) {
  const cpu = host?.cpu?.percent
  const mem = host?.mem?.percent
  const diskFree = host?.disk?.free_gb
  const diskTotal = host?.disk?.total_gb
  const hostname = host?.host?.hostname
  const os = host?.host?.os
  const diskRoot = host?.host?.disk_root

  const nvidia = Array.isArray(host?.gpu?.nvidia) ? host.gpu.nvidia : []
  const apps = Array.isArray(host?.gpu?.apps) ? host.gpu.apps : []

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
        {Array.isArray(nextActions) && nextActions.length > 0 ? (
          <div>
            {nextActions.map((x, i) => (
              <div key={i} className="small">- {x}</div>
            ))}
          </div>
        ) : (
          <div className="small">いまは平穏（危険度が上がると提案が出る）</div>
        )}
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
  return (
    <div>
      <div className="panelTitle">図鑑（モデル）</div>
      <div className="table">
        <div className="tr th">
          <div>ID</div><div>NAME</div><div>TYPE</div><div>VER</div><div>QUANT</div><div>VRAM</div><div>TAGS</div>
        </div>
        {list.map((m) => (
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
      <div className="small">PATH は backend の /api/registry で参照（運用上はパス漏洩に注意）</div>
    </div>
  )
}

function SkillsView({ skills }) {
  const list = Array.isArray(skills) ? skills : []
  return (
    <div>
      <div className="panelTitle">魔法（スキル）</div>
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
                    <div>{it.label}</div>
                    <div className="small">{it.notes || ''}</div>
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

  return (
    <div>
      <div className="panelTitle">アイテム（生成物）</div>
      <div className="small">監視フォルダ: {roots.length ? roots.map((r) => r.label).join(' / ') : '未設定（registry/items.yaml）'}</div>

      {recent.length === 0 ? (
        <div className="small">生成物が見つかりません（registry/items.yaml の path を実フォルダに合わせてね）</div>
      ) : (
        <div className="itemsGrid">
          {recent.slice(0, 60).map((it, idx) => {
            const url = `${apiBase}/files/${encodeURIComponent(it.root_id)}/${encodeRelPath(it.rel_path)}`
            return (
              <div key={`${it.root_id}:${it.rel_path}:${idx}`} className="itemCard">
                <div className="itemHead">
                  <div className="mono">{it.root_id}</div>
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
      )}
    </div>
  )
}
