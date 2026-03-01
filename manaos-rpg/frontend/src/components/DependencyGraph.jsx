// 仮: サービス依存関係グラフ（D3/vis-network等は後で追加）
export default function DependencyGraph({ services }) {
  if (!Array.isArray(services) || services.length === 0) return <div>依存関係なし</div>
  // 仮: 単純なリスト表示
  return (
    <div className="depGraph">
      <h3>サービス依存関係グラフ</h3>
      <ul>
        {services.map(s => (
          <li key={s.id}>
            <strong>{s.name}</strong>
            {Array.isArray(s.deps) && s.deps.length > 0 ? (
              <span> → 依存: {s.deps.join(', ')}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
