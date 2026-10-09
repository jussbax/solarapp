import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'

/** The one form cell: label above, the control with its unit beside it, help below. Inside a `.form-grid` the parts
 * sit on shared rows (a subgrid), so every control in a line of fields starts on the same edge whatever the labels do.
 * The label gets htmlFor and the control the same generated id, so tapping the label focuses the field and a screen
 * reader names it. The control is rendered by the child function with that id.
 *
 * The help under a control is one short line. Anything longer goes in `about`: a round "?" beside the label opens a
 * note that spans the whole grid line under the row (a lane the line makes room for), titled with the label; one
 * note is open at a time, and the button, Escape or a tap elsewhere closes it.
 *
 * A value typed for this record is tagged "override" with the way back to the default; a default carries no tag. */
const OPEN_EVENT = 'field-about-open'

export default function Field({
  label,
  hint,
  help,
  about,
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
  /** Help under the control: one short line saying what the number is. */
  help?: ReactNode
  /** The long explanation, behind the "?" beside the label. */
  about?: ReactNode
  /** The unit, printed beside the control ("₱ per kWh", "days"); at most twelve characters, never cut off. */
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
  const [open, setOpen] = useState(false)
  const [noteH, setNoteH] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const noteRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onOther = (e: Event) => {
      if ((e as CustomEvent<string>).detail !== fid) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const onTap = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener(OPEN_EVENT, onOther)
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onTap)
    return () => {
      document.removeEventListener(OPEN_EVENT, onOther)
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onTap)
    }
  }, [open, fid])

  // the lane under the row is as tall as the note, so the lines below move down instead of being covered
  useLayoutEffect(() => {
    if (!open) return
    const measure = () => setNoteH(noteRef.current?.offsetHeight ?? 0)
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [open, about])

  const toggle = () => {
    if (!open) document.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: fid }))
    setOpen(!open)
  }
  const labelText = typeof label === 'string' ? label : 'this setting'
  const tag =
    state === 'override' ? (
      <button type="button" className="field-tag override" onClick={onUseDefault} title="Typed for this record; press to go back to the default">
        <span className="tag-long">Override · use default</span>
        <span className="tag-short">Override</span>
      </button>
    ) : null
  return (
    <div className={`field ${className ?? ''}`.trim()} style={style} ref={ref} data-field={fid}>
      <div className="field-head">
        <label htmlFor={fid}>
          {label}
          {keyName && <span className="key">{keyName}</span>}
        </label>
        {about != null && about !== '' && (
          <button type="button" className="about-btn" aria-label={`About ${labelText}`} aria-expanded={open} title={`About ${labelText}`} onClick={toggle}>
            ?
          </button>
        )}
        {tag}
      </div>
      <div className="control">
        {children(fid)}
        {unit != null && unit !== '' && <span className="unit">{unit}</span>}
      </div>
      {text != null && text !== '' && <div className="help">{text}</div>}
      {about != null && about !== '' && open && (
        <div className="about-slot" style={{ height: noteH || undefined }}>
          <div className="about-note" role="note" ref={noteRef} data-testid="about-note">
            <b>{label}</b>
            <span>{about}</span>
            <button type="button" className="about-close" aria-label="Close" onClick={() => setOpen(false)}>
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
