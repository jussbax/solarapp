import type { Results } from '../types'
import Field from './Field'

export type DocState = 'ready' | 'needs_calculation' | 'needs_pricing' | 'test_weather'

const STATE_LABEL: Record<DocState, string> = {
  ready: 'Ready',
  needs_calculation: 'Needs a calculation',
  needs_pricing: 'Needs pricing',
  test_weather: 'Disabled on test weather',
}

interface DocRow {
  key: string
  name: string
  what: string
  /** Customer documents are refused on test weather data; internal ones are not. */
  customer: boolean
  /** What the document needs beyond fresh results. */
  needs: 'results' | 'pricing' | 'program'
  url: string
  inline?: boolean
  action: string
}

/** The state of one document under the one rule every document follows (the server answers 409 in the same cases). */
export function documentState(row: Pick<DocRow, 'customer' | 'needs'>, results: Results | null, stale: boolean, synthetic: boolean): { state: DocState; reason: string | null } {
  if (!results) return { state: 'needs_calculation', reason: 'Calculate first.' }
  if (stale) return { state: 'needs_calculation', reason: 'Inputs changed since the last calculation. Press Calculate first.' }
  if (row.needs === 'pricing' && !results.pricing?.available) return { state: 'needs_pricing', reason: results.pricing?.reason ?? 'Pricing needs the energy audit and the panel linked to the materials list.' }
  if (row.needs === 'program' && !results.program?.available) return { state: 'needs_pricing', reason: results.program?.reason ?? 'The program of works follows the pricing.' }
  if (row.customer && synthetic) return { state: 'test_weather', reason: 'Customer documents are disabled while test weather data is in use.' }
  return { state: 'ready', reason: null }
}

/** Every document the project produces, each with its state, in one place: the roof check PDF and card, the proposal,
 * the program of works and the two BOM exports. The card's next-step line is edited here, beside the card. */
export default function DocumentsCard({
  results,
  stale,
  synthetic,
  busy,
  nextStep,
  onNextStepChange,
  urls,
  openDocument,
}: {
  results: Results | null
  stale: boolean
  synthetic: boolean
  busy: boolean
  nextStep: string
  onNextStepChange: (v: string) => void
  /** `plans` may be left out: the plans URL then follows the program's (the same route family, api.plansUrl). */
  urls: { report: string; card: string; proposal: string; program: string; bomCsv: string; bomXlsx: string; plans?: string }
  openDocument: (url: string, inlineHint?: boolean) => void
}) {
  const plansUrl = urls.plans ?? urls.program.replace(/\/program\.pdf(\?.*)?$/, '/plans.pdf')
  const rows: DocRow[] = [
    { key: 'report', name: 'Roof check PDF', what: 'For the customer: what the roof can hold and what it would make, with the plan of each face.', customer: true, needs: 'results', url: urls.report, action: 'Download' },
    { key: 'card', name: 'Roof check card', what: 'Phone-sized image to send to the customer after the visit.', customer: true, needs: 'results', url: urls.card, inline: true, action: 'Open' },
    { key: 'proposal', name: 'Proposal PDF', what: 'For the customer: the system, the price, savings, payment terms and the milestone schedule.', customer: true, needs: 'pricing', url: urls.proposal, action: 'Download' },
    { key: 'plans', name: 'Plans for the PEE, PDF', what: 'Internal: the A3 drawing set for the Professional Electrical Engineer to sign and seal: cover and general notes, the array layout of each face at scale, the equipment and circuit schedule, and what still waits on the datasheets.', customer: false, needs: 'pricing', url: plansUrl, action: 'Download' },
    { key: 'program', name: 'Program of works PDF', what: 'Internal: the Gantt chart, the hour-by-hour plan, the pickup list and the cashflow.', customer: false, needs: 'program', url: urls.program, action: 'Download' },
    { key: 'bom-csv', name: 'Bill of materials, CSV', what: 'Internal: the BOM with your edits, for supplier orders.', customer: false, needs: 'pricing', url: urls.bomCsv, action: 'Export' },
    { key: 'bom-xlsx', name: 'Bill of materials, XLSX', what: 'Internal: the same list as a workbook.', customer: false, needs: 'pricing', url: urls.bomXlsx, action: 'Export' },
  ]
  return (
    <div>
      <div className="muted" style={{ marginBottom: 8 }}>
        One rule for every document: it is produced from the last calculation, so after any change to the inputs press Calculate first. Customer documents carry no internal costs.
      </div>
      <ul className="doc-list">
        {rows.map((r) => {
          const { state, reason } = documentState(r, results, stale, synthetic)
          const ready = state === 'ready'
          return (
            <li key={r.key} className={`doc-row ${ready ? '' : 'off'}`} data-testid={`doc-${r.key}`} data-state={state}>
              <div className="doc-main">
                <div className="doc-name">
                  {r.name} <span className={`badge ${ready ? 'good' : state === 'needs_calculation' ? 'gold' : 'neutral'} doc-state`}>{STATE_LABEL[state]}</span>
                </div>
                <div className="muted">{r.what}</div>
                {reason && <div className="muted doc-reason">{reason}</div>}
                {r.key === 'card' && (
                  <Field label="Next step printed on the card" className="doc-field" hint={`A date and time help, e.g. "Energy audit: Saturday 18 Oct, 9 am, about an hour". Blank prints the card's own line. Saved with the project.`}>
                    {(id) => <input id={id} value={nextStep} onChange={(e) => onNextStepChange(e.target.value)} placeholder="Next step: your free energy audit" maxLength={120} />}
                  </Field>
                )}
              </div>
              <div className="doc-action">
                <button type="button" disabled={!ready || busy} onClick={() => openDocument(r.url, r.inline)}>
                  {r.action}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
