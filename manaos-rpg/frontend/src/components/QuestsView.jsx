import { useState } from 'react'
import { truncateOutput } from '../utils.js'
import { fetchJson } from '../api.js'
import OutputBlock from './OutputBlock.jsx'

export default function QuestsView({ quests, apiBase, onRunAction, actionResult, runningAction }) {
  const list = Array.isArray(quests) ? quests : []
  const [questLoading, setQuestLoading] = useState('')
  const [questResult, setQuestResult] = useState(null)

  async function runApiQuest(endpoint) {
    setQuestLoading(endpoint)
    setQuestResult(null)
    try {
      const r = await fetchJson(endpoint)
      const text = JSON.stringify(r, null, 2)
      setQuestResult({ endpoint, text: truncateOutput(text), ok: true })
    } catch (e) {
      setQuestResult({ endpoint, text: `ERR: ${String(e?.message || e)}`, ok: false })
    } finally {
      setQuestLoading('')
    }
  }
  return (
    <div>
      <div className="panelTitle">クエスト（タスク） <span className="small">{list.length}件</span></div>
      <div className="small">kind=api はクリック（GET）/ kind=action は実行（POST, backendで許可されたもののみ）</div>
      {actionResult ? (
        <div className="box mb12">
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
        <div className="tr th colsQuests">
          <div>ID</div><div>LABEL</div><div>KIND</div><div>ENDPOINT</div><div>ACTION</div>
        </div>
        {list.map((q) => (
          <div key={q.id} className="tr colsQuests">
            <div className="mono">{q.id}</div>
            <div>{q.label}</div>
            <div className="mono">{q.kind}</div>
            <div className="mono">{q.endpoint ?? q.action_id ?? '—'}</div>
            <div>
              {q.kind === 'api' && q.endpoint ? (
                <button className="link" disabled={!!questLoading} onClick={() => runApiQuest(q.endpoint)}>
                  {questLoading === q.endpoint ? '実行中…' : '実行'}
                </button>
              ) : q.kind === 'action' && q.action_id ? (
                <button className="link" disabled={!!runningAction} onClick={() => onRunAction?.(q.action_id)}>{runningAction === q.action_id ? '実行中…' : '実行'}</button>
              ) : (
                <span className="small">—</span>
              )}
            </div>
          </div>
        ))}
      </div>
      {questResult ? (
        <div className="mt12">
          <div className="small">結果: <span className="mono">{questResult.endpoint}</span></div>
          <OutputBlock text={questResult.text} onClear={() => setQuestResult(null)} />
        </div>
      ) : null}
    </div>
  )
}
