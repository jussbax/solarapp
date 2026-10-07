import { useEffect, useState } from 'react'

/** Number input that tolerates partial typing and empty values. */
export default function NumberInput({
  value,
  onChange,
  allowEmpty = false,
  step,
  min,
  max,
  placeholder,
  style,
}: {
  value: number | null
  onChange: (v: number | null) => void
  allowEmpty?: boolean
  step?: number | string
  min?: number
  max?: number
  placeholder?: string
  style?: React.CSSProperties
}) {
  const [text, setText] = useState(value == null ? '' : String(value))
  useEffect(() => {
    setText(value == null ? '' : String(value))
  }, [value])
  return (
    <input
      type="number"
      inputMode="decimal"
      step={step ?? 'any'}
      min={min}
      max={max}
      placeholder={placeholder}
      style={style}
      value={text}
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
        if (text === '' && !allowEmpty) setText(value == null ? '' : String(value))
      }}
    />
  )
}
