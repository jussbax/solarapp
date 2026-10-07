import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { MaterialItem } from '../types'

/** Search box over the materials database; calls onPick with the chosen item. */
export default function MaterialPicker({
  category,
  placeholder,
  onPick,
  autoFocus,
}: {
  category?: string
  placeholder?: string
  onPick: (item: MaterialItem) => void
  autoFocus?: boolean
}) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<MaterialItem[]>([])
  const [open, setOpen] = useState(false)
  const timer = useRef<number | null>(null)
  useEffect(() => {
    if (!open) return
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      api.materials({ q, category, limit: 12 }).then(setItems).catch(() => setItems([]))
    }, 150)
  }, [q, open, category])
  return (
    <div className="suggest">
      <input
        value={q}
        autoFocus={autoFocus}
        placeholder={placeholder ?? 'Search the materials database'}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && items.length > 0 && (
        <div className="suggest-list">
          {items.map((it) => (
            <div
              key={it.code}
              className="suggest-item"
              onMouseDown={() => {
                onPick(it)
                setQ('')
                setOpen(false)
              }}
            >
              <b>{it.code}</b> {it.name} <span className="muted">{it.supplier} · {it.list_price.toLocaleString()} PHP/{it.unit}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
