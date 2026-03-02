export default function Box({ title, children, style, className }) {
  return (
    <div className={`box${className ? ' ' + className : ''}`} style={style}>
      <div className="boxTitle">{title}</div>
      <div className="boxBody">{children}</div>
    </div>
  )
}
