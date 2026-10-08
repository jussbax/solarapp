import { useId, type CSSProperties, type ReactNode } from 'react'

/** A label attached to its control: the label gets htmlFor and the control the same generated id, so tapping the label
 * focuses the field and a screen reader names it. The control is rendered by the child function with that id. */
export default function Field({
  label,
  hint,
  id,
  className,
  style,
  children,
}: {
  label: ReactNode
  /** Help under the control, visible (not only in a title). */
  hint?: ReactNode
  /** An explicit id when the field is rendered in a list; otherwise one is generated. */
  id?: string
  className?: string
  style?: CSSProperties
  children: (id: string) => ReactNode
}) {
  const auto = useId()
  const fid = id ?? auto
  return (
    <div className={className} style={style}>
      <label htmlFor={fid}>{label}</label>
      {children(fid)}
      {hint && <div className="hint">{hint}</div>}
    </div>
  )
}
