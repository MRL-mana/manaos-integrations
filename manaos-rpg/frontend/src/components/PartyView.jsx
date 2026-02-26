import { useMemo } from 'react'

export default function PartyView({ services }) {
  const list = useMemo(() => {
    const raw = Array.isArray(services) ? services : []
    return raw.slice().sort((a, b) => {
      if (a.alive === b.alive) return 0
      return a.alive ? 1 : -1
    })
  }, [services])
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
          <div key={s.id} className={s.alive ? 'tr' : 'tr trDanger'}>
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
