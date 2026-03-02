export default function QuestStats({ history }) {
  if (!Array.isArray(history) || history.length === 0) return <div>履歴なし</div>
  const success = history.filter(h => h.ok).length
  const total = history.length
  const rate = total > 0 ? Math.round((success / total) * 100) : 0
  return (
    <div className="questStats">
      <h3>クエスト実行履歴・統計</h3>
      <div>成功率: <span className={rate >= 80 ? 'ok' : rate >= 50 ? 'caution' : 'danger'}>{rate}%</span> ({success}/{total})</div>
      <ul>
        {history.slice(-10).reverse().map((h, i) => (
          <li key={i}>
            <span className={h.ok ? 'ok' : 'danger'}>{h.ok ? '✔' : '✗'}</span> {h.label} <span className="small">{h.ts}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
