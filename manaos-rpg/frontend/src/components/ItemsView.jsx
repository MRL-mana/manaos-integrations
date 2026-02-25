import { useState, useMemo } from 'react'
import { ITEMS_SHOW_LIMIT, encodeRelPath, fmtTs, fmtBytes } from '../utils.js'

export default function ItemsView({ items, apiBase }) {
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
                  const limit = expanded ? groupItems.length : ITEMS_SHOW_LIMIT
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
                      {!expanded && groupItems.length > ITEMS_SHOW_LIMIT ? (
                        <div className="fullSpan showMore">
                          <button className="link" onClick={() => setExpandedGroups((prev) => new Set(prev).add(rid))}>
                            もっと見る（残り {groupItems.length - ITEMS_SHOW_LIMIT}件）
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
