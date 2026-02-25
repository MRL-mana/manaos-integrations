import React, { useMemo } from 'react'

export default function MapView({ devices }) {
  const list = Array.isArray(devices) ? devices : []
  const aliveDevices = useMemo(() => list.filter((d) => d.alive), [list])
  return (
    <div>
      <div className="panelTitle">マップ（デバイス） <span className="small">{list.length}件{list.length > 0 ? ` / ${aliveDevices.length} online` : ''}</span></div>
      {list.length === 0 ? (
        <div className="small">デバイスが未登録です（registry/devices.yaml を追加）</div>
      ) : (
        <div className="table">
          <div className="tr th colsMap">
            <div>ID</div><div>NAME</div><div>KIND</div><div>STATUS</div><div>TAGS</div>
          </div>
          {list.map((d) => (
            <div key={d.id} className={`tr colsMap${typeof d.alive === 'boolean' && !d.alive ? ' trDanger' : ''}`}>
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
