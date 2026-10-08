// Embeddable widget for the company website:
//   <div id="pld-solar-estimate"></div>
//   <script src="https://solar.pldevinc.com/widget/quick.js" defer></script>
// The script finds the div (or makes one after itself), injects its styles and calls
// the server it was loaded from (override with data-api="https://..." on the script tag).
import { createRoot } from 'react-dom/client'
import css from './estimate.css?inline'
import Estimate from './Estimate'

function mount() {
  const script = (document.currentScript as HTMLScriptElement | null) ?? (Array.from(document.scripts).find((s) => s.src.includes('/widget/quick.js')) as HTMLScriptElement | undefined)
  const explicit = script?.dataset.api
  let apiBase = explicit ? explicit.replace(/\/$/, '') : ''
  if (!apiBase && script?.src) {
    try {
      apiBase = new URL(script.src).origin
    } catch {
      apiBase = ''
    }
  }
  let host = document.getElementById(script?.dataset.target || 'pld-solar-estimate')
  if (!host) {
    host = document.createElement('div')
    host.id = 'pld-solar-estimate'
    if (script?.parentNode) script.parentNode.insertBefore(host, script.nextSibling)
    else document.body.appendChild(host)
  }
  if (!document.getElementById('pld-estimate-style')) {
    const style = document.createElement('style')
    style.id = 'pld-estimate-style'
    style.textContent = css
    document.head.appendChild(style)
  }
  createRoot(host).render(<Estimate apiBase={apiBase} />)
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
else mount()
