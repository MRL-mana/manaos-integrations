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

export default function StatusView({ host, services, models, devices, skills, danger, rlAnything, autonomy, nextActions, nextActionHints, onRunAction, actionResult, actionsEnabled, runningAction }) {
  const [showConfig, setShowConfig] = useState(false)
  const [manualCheck, setManualCheck] = useState(null)
  const [manualSaving, setManualSaving] = useState(false)
  const [manualMsg, setManualMsg] = useState('')
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
        <GaugeBar label={diskRoot || 'C:'} pct={diskTotal > 0 ? ((diskTotal - (diskFree ?? 0)) / diskTotal) * 100 : 0} />
        <div className="small" style={{ marginTop: 4 }}>free {diskFree ?? '—'}GB / total {diskTotal ?? '—'}GB</div>
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
      {/* DashboardConfig モーダル */}
      {showConfig && (
        <DashboardConfig onClose={() => setShowConfig(false)} />
      )}
    </div>
  )
}
