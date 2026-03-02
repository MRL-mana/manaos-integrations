import { useMemo } from 'react'

/**
 * 横帯でサービス稼働状況を色セグメントで表示するミニコンポーネント。
 * ヘッダーに常時表示して一目で全体把握。
 */
const TAG_COLORS = {
  always_on:   '#FF6B6B',
  core:        '#FF9F6B',
  ai:          '#FFE66B',
  chat:        '#7CFF6B',
  monitoring:  '#6BB5FF',
  automation:  '#B56BFF',
  docker:      '#FF6BB5',
  mcp:         '#6BFFDA',
}

function pickColor(tags) {
  if (!Array.isArray(tags)) return '#555'
  for (const t of tags) {
    if (TAG_COLORS[t]) return TAG_COLORS[t]
  }
  return '#555'
}

export default function HealthStrip({ services }) {
  const svcs = useMemo(() => (Array.isArray(services) ? services : []), [services])

  if (svcs.length === 0) return null

  const total = svcs.length
  const alive = svcs.filter((s) => s.alive).length
  const pct = Math.round((alive / total) * 100)

  return (
    <div className="healthStrip" title={`${alive}/${total} alive (${pct}%)`}>
      <div className="healthStripBar">
        {svcs.map((s) => {
          const color = pickColor(s.tags)
          return (
            <div
              key={s.id}
              className="healthStripSeg"
              style={{
                flex: 1,
                background: s.alive ? color : 'rgba(255,255,255,0.06)',
                opacity: s.alive ? 0.85 : 0.25,
              }}
              title={`${s.id}: ${s.alive ? 'UP' : 'DOWN'}`}
            />
          )
        })}
      </div>
      <div className="healthStripLabel">
        <span className={pct >= 50 ? 'ok' : 'danger'}>{alive}</span>
        <span className="dim">/{total}</span>
        <span className="dim">({pct}%)</span>
      </div>
    </div>
  )
}
