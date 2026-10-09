import { useEffect, useState } from 'react'

/** Number input that tolerates partial typing and empty values. Right-aligned, tabular figures (styles.css). */
export default function NumberInput({
  value,
  onChange,
  allowEmpty = false,
  step,
  min,
  max,
  placeholder,
  style,
  id,
  ariaLabel,
  disabled,
  className,
}: {
  value: number | null
  onChange: (v: number | null) => void
  allowEmpty?: boolean
  step?: number | string
  min?: number
  max?: number
  placeholder?: string
  style?: React.CSSProperties
  /** Set by Field so the label's htmlFor points here. */
  id?: string
  /** The accessible name when the input sits in a table cell with no label of its own. */
  ariaLabel?: string
  disabled?: boolean
  className?: string
}) {
  const [text, setText] = useState(value == null ? '' : String(value))
  useEffect(() => {
    setText(value == null ? '' : String(value))
  }, [value])
  return (
    <input
      id={id}
      type="number"
      inputMode="decimal"
      step={step ?? 'any'}
      min={min}
      max={max}
      placeholder={placeholder}
      style={style}
      value={text}
      aria-label={ariaLabel}
      disabled={disabled}
      className={className}
      onChange={(e) => {
        setText(e.target.value)
        if (e.target.value === '') {
          if (allowEmpty) onChange(null)
          return
        }
        const n = parseFloat(e.target.value)
        if (Number.isFinite(n)) onChange(n)
      }}
      onBlur={() => {
        // a cleared field shows the value in force again (the default a project input fell back to, or the kept value)
        if (text === '' && (value != null || !allowEmpty)) setText(value == null ? '' : String(value))
      }}
    />
  )
}
