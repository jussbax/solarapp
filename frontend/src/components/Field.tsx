import { useId, type CSSProperties, type ReactNode } from 'react'

/** The one form cell: label above, the control with its unit beside it, help below. Inside a `.form-grid` the three parts
 * sit on shared rows (a subgrid), so every control in a line of fields starts on the same edge whatever the labels do.
 * The label gets htmlFor and the control the same generated id, so tapping the label focuses the field and a screen
 * reader names it. The control is rendered by the child function with that id.
 *
 * A value that comes from a default is shown filled and tagged "default"; an override is tagged and offers the way back. */
export default function Field({
  label,
  hint,
  help,
  unit,
  keyName,
  state,
  onUseDefault,
  id,
  className,
  style,
  children,
}: {
  label: ReactNode
  /** Help under the control (an alias of `help`, kept for the callers that use it). */
  hint?: ReactNode
  /** Help under the control, visible (not only in a title). */
  help?: ReactNode
  /** The unit, printed beside the control ("₱ per kWh", "days"). */
  unit?: ReactNode
  /** A settings key printed in small monospace under the label (the BOM roles). */
  keyName?: string
  /** Where the value in force comes from: a default from the settings, or an override typed for this record. */
  state?: 'default' | 'override'
  /** Back to the default; rendered as the override tag's action. */
  onUseDefault?: () => void
  /** An explicit id when the field is rendered in a list; otherwise one is generated. */
  id?: string
  className?: string
  style?: CSSProperties
  children: (id: string) => ReactNode
}) {
  const auto = useId()
  const fid = id ?? auto
  const text = help ?? hint
  const tag =
    state === 'override' ? (
      <button type="button" className="field-tag override" onClick={onUseDefault} title="Typed for this record; press to go back to the default">
        <span className="tag-long">override · use default</span>
        <span className="tag-short">override</span>
      </button>
    ) : state === 'default' ? (
      <span className="field-tag" title="From the settings; type a value to override it for this record">
        default
      </span>
    ) : null
  return (
    <div className={`field ${className ?? ''}`.trim()} style={style}>
      <div className="field-head">
        <label htmlFor={fid}>
          {label}
          {keyName && <span className="key">{keyName}</span>}
        </label>
        {tag}
      </div>
      <div className="control">
        {children(fid)}
        {unit != null && unit !== '' && <span className="unit">{unit}</span>}
      </div>
      {text != null && text !== '' && <div className="help">{text}</div>}
    </div>
  )
}
