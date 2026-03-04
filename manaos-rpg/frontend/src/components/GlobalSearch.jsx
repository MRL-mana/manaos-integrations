import { useState, useMemo, useEffect, useRef, useCallback } from 'react'

/**
 * Ctrl+K でオーバーレイ表示するグローバル検索。
 * サービス / モデル / デバイス / スキル をまとめて横断検索。
 */
const CAT_ICONS = {
  service: '⚔️',
  model: '🧠',
  device: '🗺️',
  skill: '✨',
  nav: '🗂️',
}

function buildIndex(state) {
  const items = []
  if (Array.isArray(state?.services)) {
    for (const s of state.services) {
      items.push({
        cat: 'service',
        id: s.id,
        label: s.name || s.id,
        sub: [s.kind, s.port ? `:${s.port}` : '', ...(s.tags || [])].filter(Boolean).join(' · '),
        alive: s.alive,
        tab: 'party',
      })
    }
  }
  if (Array.isArray(state?.models)) {
    for (const m of state.models) {
      items.push({
        cat: 'model',
        id: m.id,
        label: m.name || m.id,
        sub: [m.type, m.runtime, m.vram_gb ? `${m.vram_gb}GB` : ''].filter(Boolean).join(' · '),
        alive: m.loaded,
        tab: 'bestiary',
      })
    }
  }
  if (Array.isArray(state?.devices)) {
    for (const d of state.devices) {
      items.push({
        cat: 'device',
        id: d.id,
        label: d.name || d.id,
        sub: [d.kind, d.os, ...(d.tags || [])].filter(Boolean).join(' · '),
        alive: d.alive,
        tab: 'map',
      })
    }
  }
  if (Array.isArray(state?.skills)) {
    for (const s of state.skills) {
      items.push({
        cat: 'skill',
        id: s.id,
        label: s.name || s.id,
        sub: [s.category, ...(s.tags || [])].filter(Boolean).join(' · '),
        alive: true,
        tab: 'skills',
      })
    }
  }
  // 固定ナビゲーションエントリー（常時検索可能）
  items.push({ cat: 'nav', id: 'lessons', label: '教訓（成長ログ）', sub: '指摘・修正パターン / Lキー', alive: true, tab: 'lessons' })
  items.push({ cat: 'nav', id: 'agents', label: 'エージェント追跡', sub: 'ランク・品質スコア / Aキー', alive: true, tab: 'agents' })
  items.push({ cat: 'nav', id: 'revenue', label: '収益（KPI）', sub: 'Billing / RL / 品質 / 0キー', alive: true, tab: 'revenue' })
  return items
}

export default function GlobalSearch({ state, onNavigate }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)

  const index = useMemo(() => buildIndex(state), [state])

  const results = useMemo(() => {
    if (!query.trim()) return index.slice(0, 20)
    const q = query.trim().toLowerCase()
    return index.filter(
      (it) =>
        it.id.toLowerCase().includes(q) ||
        it.label.toLowerCase().includes(q) ||
        it.sub.toLowerCase().includes(q)
    ).slice(0, 30)
  }, [index, query])

  const [sel, setSel] = useState(0)

  const close = useCallback(() => {
    setOpen(false)
    setQuery('')
  }, [])

  useEffect(() => {
    function handleKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
      if (e.key === 'Escape' && open) {
        e.preventDefault()
        close()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, close])

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  function handleItemKey(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSel((s) => Math.min(s + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSel((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter' && results[sel]) {
      onNavigate?.(results[sel].tab)
      close()
    }
  }

  if (!open) return null

  return (
    <div className="gsOverlay" onClick={close}>
      <div className="gsDialog" onClick={(e) => e.stopPropagation()} onKeyDown={handleItemKey}>
        <div className="gsInputRow">
          <span className="gsIcon">🔍</span>
          <input
            ref={inputRef}
            className="gsInput"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSel(0)
            }}
            placeholder="サービス / モデル / デバイス / スキル を検索…  (Esc で閉じる)"
            spellCheck={false}
          />
          <kbd className="gsKbd">Esc</kbd>
        </div>

        <div className="gsResults">
          {results.length === 0 ? (
            <div className="gsEmpty">一致なし</div>
          ) : (
            results.map((it, idx) => (
              <button
                key={`${it.cat}:${it.id}`}
                className={`gsResult${idx === sel ? ' gsResultSel' : ''}`}
                onMouseEnter={() => setSel(idx)}
                onClick={() => { onNavigate?.(it.tab); close() }}
              >
                <span className="gsResultIcon">{CAT_ICONS[it.cat] || '❓'}</span>
                <div className="gsResultBody">
                  <span className="gsResultLabel">{it.label}</span>
                  <span className="gsResultSub">{it.sub}</span>
                </div>
                <span className={it.alive ? 'gsResultStatus ok' : 'gsResultStatus danger'}>
                  {it.alive ? '●' : '○'}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="gsFooter">
          <span>↑↓ 移動</span>
          <span>Enter で遷移</span>
          <span>Esc で閉じる</span>
          <span className="gsCount">{results.length}/{index.length}</span>
        </div>
      </div>
    </div>
  )
}
