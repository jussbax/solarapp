import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useNarrow } from './responsive'
import '../accounts.css'

/* The dialog kit the account screens are built on: a question is asked at the moment of the action, never in a
 * standing form. `Dialog` is the one modal (focus trap, Escape and the backdrop cancel, a sheet from the bottom on the
 * phone, 44 px targets); `Menu` is the "⋯" menu (a popover on the desk, a sheet on the phone); `CopyBox` shows a secret
 * once with a Copy button. The toast and the other helpers live in ../accounts.tsx. */

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function Dialog({
  open,
  title,
  onClose,
  children,
  footer,
  tall = false,
  wide = false,
  testId,
}: {
  open: boolean
  title: ReactNode
  /** Escape, the backdrop and the Cancel button all call this. */
  onClose: () => void
  children: ReactNode
  /** The buttons; the primary one is the only black button. */
  footer?: ReactNode
  /** A full-height sheet on the phone (the Add a person form). */
  tall?: boolean
  wide?: boolean
  testId?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const closeRef = useRef(onClose)
  const titleId = useId()
  useEffect(() => {
    closeRef.current = onClose
  })

  // focus goes in on open and back where it was on close; Tab cycles inside; Escape cancels; the page behind does not scroll
  useEffect(() => {
    if (!open) return
    const el = ref.current
    if (!el) return
    const before = document.activeElement as HTMLElement | null
    // React has already focused an `autoFocus` field by now (it renders no attribute); otherwise the dialog itself takes focus
    if (!el.contains(document.activeElement)) (el.querySelector<HTMLElement>('[data-autofocus]') ?? el).focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        closeRef.current()
        return
      }
      if (e.key !== 'Tab') return
      const items = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((x) => x.offsetParent !== null)
      if (items.length === 0) {
        e.preventDefault()
        return
      }
      const i = items.indexOf(document.activeElement as HTMLElement)
      if (e.shiftKey && i <= 0) {
        e.preventDefault()
        items[items.length - 1].focus()
      } else if (!e.shiftKey && (i === -1 || i === items.length - 1)) {
        e.preventDefault()
        items[0].focus()
      }
    }
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      before?.focus?.()
    }
  }, [open])

  if (!open) return null
  return createPortal(
    <div
      className="dlg-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div ref={ref} className={`dlg ${tall ? 'tall' : ''} ${wide ? 'wide' : ''}`.trim()} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} data-testid={testId}>
        <div className="dlg-head">
          <h2 id={titleId}>{title}</h2>
        </div>
        <div className="dlg-body">{children}</div>
        {footer && <div className="dlg-foot">{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}

export type MenuItem = { label: string; onSelect: () => void; danger?: boolean }

/** The "⋯" button and its menu. On the desk a popover under the button; on the phone a sheet titled with the person's name. */
export function Menu({ label, title, items, testId }: { label: string; title: string; items: MenuItem[]; testId?: string }) {
  const [open, setOpen] = useState(false)
  const narrow = useNarrow()
  const wrap = useRef<HTMLDivElement>(null)
  const btn = useRef<HTMLButtonElement>(null)

  // the desk popover: a click outside or Escape closes it; arrows move between the items
  useEffect(() => {
    if (!open || narrow) return
    const onDown = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      const el = wrap.current
      if (!el) return
      const list = Array.from(el.querySelectorAll<HTMLElement>('.menu-item'))
      const i = list.indexOf(document.activeElement as HTMLElement)
      if (e.key === 'Escape') {
        e.stopPropagation()
        setOpen(false)
        btn.current?.focus()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        list[(i + 1) % list.length]?.focus()
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        list[(i - 1 + list.length) % list.length]?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    wrap.current?.querySelector<HTMLElement>('.menu-item')?.focus()
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, narrow])

  const pick = (it: MenuItem) => {
    setOpen(false)
    it.onSelect()
  }
  const list = items.map((it, i) => (
    <button key={i} type="button" role="menuitem" className={`menu-item ${it.danger ? 'danger' : ''}`.trim()} onClick={() => pick(it)}>
      {it.label}
    </button>
  ))

  return (
    <div className="menu-wrap" ref={wrap}>
      <button ref={btn} type="button" className="menu-btn" aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)} data-testid={testId}>
        ⋯
      </button>
      {open && !narrow && (
        <div className="menu-pop" role="menu" aria-label={label}>
          {list}
        </div>
      )}
      {open && narrow && (
        <Dialog open title={title} onClose={() => setOpen(false)} testId={testId ? `${testId}-sheet` : undefined}>
          <div className="menu-sheet" role="menu" aria-label={label}>
            {list}
          </div>
        </Dialog>
      )}
    </div>
  )
}

/** Copies the text; the button reads "Copied" for two seconds. Where the clipboard is blocked the caller's text is
 *  `user-select: all`, so the button selects it instead and says so. */
export function CopyButton({ value, label = 'Copy', onCopied, selectFrom }: { value: string; label?: string; onCopied?: () => void; selectFrom?: () => HTMLElement | null }) {
  const [state, setState] = useState<'idle' | 'done' | 'select'>('idle')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setState('done')
      onCopied?.()
    } catch {
      const el = selectFrom?.()
      if (el) {
        const range = document.createRange()
        range.selectNodeContents(el)
        const sel = window.getSelection()
        sel?.removeAllRanges()
        sel?.addRange(range)
      }
      setState('select')
    }
    window.setTimeout(() => setState('idle'), 2000)
  }
  return (
    <button type="button" className={state === 'done' ? 'primary' : ''} onClick={copy} aria-live="polite" data-testid="copy">
      {state === 'done' ? 'Copied' : state === 'select' ? 'Selected: copy it' : label}
    </button>
  )
}

/** A secret shown once (a temporary password, the typed authenticator key), in monospace with Copy beside it. */
export function CopyBox({ value, small = false, label, onCopied }: { value: string; small?: boolean; label: string; onCopied?: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div className="copy-box">
      <div ref={ref} className={`copy-value ${small ? 'small-mono' : ''}`.trim()} aria-label={label} data-testid="copy-value">
        {value}
      </div>
      <CopyButton value={value} onCopied={onCopied} selectFrom={() => ref.current} />
    </div>
  )
}
