import { useMemo } from 'react'

export default function SystemsView({ unified, onRunAction, actionResult, actionsEnabled, runningAction }) {
  const base = unified?.base
  const r = unified?.integrations
  const ok = Boolean(r?.ok)
  const data = r?.data && typeof r.data === 'object' ? r.data : null

  const mrl = unified?.mrl_memory
  const mrlOk = Boolean(mrl?.ok)
  const mrlBase = mrl?.base
  const mrlHealth = mrl?.health && typeof mrl.health === 'object' ? mrl.health : null
  const mrlCfg = mrl?.metrics?.config && typeof mrl.metrics.config === 'object' ? mrl.metrics.config : null

  const health = data?.health && typeof data.health === 'object' ? data.health : null
  const openapi = data?.openapi && typeof data.openapi === 'object' ? data.openapi : null

  const rows = useMemo(() => {
    if (!data) return []
    return Object.entries(data).map(([k, v]) => ({
      key: k,
      name: v?.name,
      available: Boolean(v?.available),
      reason: v?.reason
    }))
  }, [data])

  return (
    <div>
      <div className="panelTitle">システム（統合）</div>
      <div className="small">Unified API: <span className="mono">{base || '—'}</span></div>
      <div className="small">integrations/status: {ok ? <span className="ok">OK</span> : <span className="danger">NG</span>} / auth_configured={String(Boolean(r?.auth_configured))}</div>
      {!ok ? (
        <div className="err">{String(r?.error || 'unavailable')}</div>
      ) : null}

      {health || openapi ? (
        <div className="sectionBlock mt10">
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
              <div className="mt10">
                <div className="kv"><span>title</span><span className="mono">{String(openapi.title || '—')}</span></div>
                <div className="kv"><span>version</span><span className="mono">{String(openapi.version || '—')}</span></div>
                <div className="kv"><span>paths</span><span className="mono">{String(openapi.paths_count ?? '—')}</span></div>
                {Array.isArray(openapi.paths_sample) && openapi.paths_sample.length ? (
                  <div className="small">sample: <span className="mono">{openapi.paths_sample.slice(0, 10).join(' , ')}</span></div>
                ) : null}
              </div>
            ) : (
              <div className="small mt10">openapi: —</div>
            )}
          </div>
        </div>
      ) : null}

      <div className="sectionBlock mt10">
        <div className="sectionHead">
          <span className="mono">MRL</span>
          <span>mrl-memory status</span>
          <span className="small">（Unified memory 503時のフォールバック）</span>
        </div>
        <div className="boxBody">
          <div className="small">base: <span className="mono">{String(mrlBase || '—')}</span></div>
          <div className="small">health: {mrlOk ? <span className="ok">OK</span> : <span className="danger">NG</span>}</div>
          {mrlHealth ? (
            <div className="mt8">
              <div className="kv"><span>service</span><span className="mono">{String(mrlHealth.service || '—')}</span></div>
              <div className="kv"><span>status</span><span className={String(mrlHealth.status) === 'healthy' ? 'ok' : 'caution'}>{String(mrlHealth.status || '—')}</span></div>
              {typeof mrlHealth.auth_required !== 'undefined' ? (
                <div className="kv"><span>auth</span><span className="mono">{String(mrlHealth.auth_required)}</span></div>
              ) : null}
            </div>
          ) : null}
          {mrlCfg ? (
            <div className="mt8">
              <div className="kv"><span>write_mode</span><span className="mono">{String(mrlCfg.write_mode || '—')}</span></div>
              <div className="kv"><span>write_enabled</span><span className="mono">{String(mrlCfg.write_enabled || '—')}</span></div>
            </div>
          ) : null}

          <div className="skillActions mt10">
            <button
              className="link"
              disabled={actionsEnabled === false || !!runningAction}
              onClick={() => onRunAction?.('mrl_memory_write_on_full')}
            >
              {runningAction === 'mrl_memory_write_on_full' ? '実行中…' : '書き込みON（full）'}
            </button>
            <button
              className="link"
              disabled={actionsEnabled === false || !!runningAction}
              onClick={() => onRunAction?.('mrl_memory_write_off')}
            >
              {runningAction === 'mrl_memory_write_off' ? '実行中…' : '書き込みOFF（readonly）'}
            </button>
            {actionsEnabled === false ? <span className="caution">actions disabled</span> : null}
          </div>

          {actionResult?.action_id === 'mrl_memory_write_on_full' || actionResult?.action_id === 'mrl_memory_write_off' ? (
            <div className="sectionBlock mt8">
              <div className="small">last action: <span className="mono">{String(actionResult.action_id || '—')}</span></div>
              <div className="small">ok: {String(Boolean(actionResult?.result?.ok))}</div>
            </div>
          ) : null}
        </div>
      </div>

      {rows.length > 0 ? (
        <div className="sectionBlock mt10">
          <div className="sectionHead">
            <span className="mono">INTEGRATIONS</span>
            <span>サービス一覧</span>
            <span className="small">{rows.length}件</span>
          </div>
          <div className="table">
            <div className="tr th colsToolAvail">
              <div>KEY</div><div>NAME</div><div>AVAILABLE</div><div>REASON</div>
            </div>
            {rows.map((x) => (
              <div key={x.key} className={`tr colsToolAvail${x.available ? '' : ' trDanger'}`}>
                <div className="mono">{x.key}</div>
                <div>{x.name || '—'}</div>
                <div className={x.available ? 'ok' : 'danger'}>{x.available ? 'YES' : 'NO'}</div>
                <div className="small">{x.reason || '—'}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="small mt10">データなし（APIキー未設定/認証NG の可能性）</div>
      )}
      <div className="small">必要なら環境変数で <span className="mono">MANAOS_UNIFIED_API_KEY</span>（または <span className="mono">MANAOS_INTEGRATION_READONLY_API_KEY</span>）をRPG backend側に渡す</div>
    </div>
  )
}
