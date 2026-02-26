import { useMemo } from 'react'
import { bar, fmtBytes } from '../utils.js'
import Box from './Box.jsx'
import OutputBlock from './OutputBlock.jsx'

export default function StatusView({ host, nextActions, nextActionHints, onRunAction, actionResult, actionsEnabled, runningAction }) {
  const cpu = host?.cpu?.percent
  const mem = host?.mem?.percent
  const diskFree = host?.disk?.free_gb
  const diskTotal = host?.disk?.total_gb
  const hostname = host?.host?.hostname
  const os = host?.host?.os
  const diskRoot = host?.host?.disk_root

  const nvidia = Array.isArray(host?.gpu?.nvidia) ? host.gpu.nvidia : []
  const apps = Array.isArray(host?.gpu?.apps) ? host.gpu.apps : []

  const hints = useMemo(() => (Array.isArray(nextActionHints) ? nextActionHints : []), [nextActionHints])
  const actions = useMemo(() => (Array.isArray(nextActions) ? nextActions : []), [nextActions])

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
              {typeof g.utilization_gpu === 'number' ? (
                <div className="mono gpuDetail">UTIL {bar(g.utilization_gpu)}</div>
              ) : (
                <div className="small gpuDetail">UTIL —</div>
              )}
              {typeof g.mem_used_mb === 'number' && typeof g.mem_total_mb === 'number' && g.mem_total_mb > 0 ? (
                <div className="mono gpuDetail">VRAM {bar((g.mem_used_mb / g.mem_total_mb) * 100)} ({g.mem_used_mb}MB / {g.mem_total_mb}MB)</div>
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
    </div>
  )
}
