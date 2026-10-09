import { useEffect, useState } from 'react'
import { roundTo } from './shared'

/** Number input that tolerates partial typing and empty values. Right-aligned, tabular figures (styles.css).
 * With `decimals` the shown value is rounded as a person would say it (0.893854748603352 reads 0.89) while the stored
 * value keeps its precision until the owner retypes it; `step` then defaults to one unit of the last decimal. */
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
  decimals,
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
  /** Decimals shown for the quantity kind (money 0, hours 2, percent 1, ...); undefined shows the value as stored. */
  decimals?: number
}) {
  const fmt = (v: number | null) => (v == null ? '' : decimals == null ? String(v) : String(roundTo(v, decimals)))
  const [text, setText] = useState(fmt(value))
  useEffect(() => {
    // follow the value from outside, but never fight the typist: a typed "0.891" equals the stored 0.891
    const typed = parseFloat(text)
    if (value == null ? text !== '' : !(Number.isFinite(typed) && typed === value)) setText(fmt(value))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])
  return (
    <input
      id={id}
      type="number"
      inputMode={decimals === 0 ? 'numeric' : 'decimal'}
      step={step ?? (decimals == null ? 'any' : decimals === 0 ? 1 : 10 ** -decimals)}
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
        if (text === '' && (value != null || !allowEmpty)) setText(fmt(value))
      }}
    />
  )
}
