import type { BatteryAutonomy, PricedLine, PricingChoices, Results, SizingBlock, Warning } from '../types'
import AuditResults, { KIND_LABEL } from './AuditResults'
import { plural } from '../fmt'

const n0 = (v: number) => Math.round(v).toLocaleString()
const n1 = (v: number) => v.toFixed(1)
const n2 = (v: number) => v.toFixed(2)
const pct1 = (v: number) => `${(v * 100).toFixed(1)}%`
const qty = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))

/** The BOQ warnings that are about the electrical design; the rest (freight, missing codes) stay in Quantities. */
const DESIGN_CODES = new Set([
  'inverter_not_grid_interactive', 'inverter_certificate_unknown', 'default_inverter_not_grid', 'default_inverter', 'no_inverter', 'no_battery',
  'battery_current_unknown', 'battery_current_units', 'battery_current', 'battery_breaker', 'battery_cable', 'pv_cable', 'ac_cable', 'ac_breaker', 'ats',
])

const gridFlag = (v: boolean | null | undefined) => (v === true ? 'grid-interactive (can export)' : v === false ? 'not grid-interactive (cannot export)' : 'grid-interactive status unknown')

/** System design: the inverter with its certificate and grid-interactive status, the battery (nominal and usable),
 * autonomy and loss of load, strings, cable gauges with their voltage drop, breakers and surge protectors, the panels per
 * face, and the energy balance the sizing rests on. Everything comes from the sizing block and the BOQ meta that already
 * exist; nothing is computed here. */
export default function SystemDesign({ results, panelName, panelWp }: { results: Results; panelName: string; panelWp: number }) {
  const sizing = results.sizing
  const pricing = results.pricing
  const audit = results.audit
  if (!audit || !sizing) {
    return <div className="muted">The system design follows the energy audit: fill in the appliances and the bill, then Calculate.</div>
  }
  const priced = !!pricing?.available
  const ch = priced ? ((pricing!.choices ?? {}) as PricingChoices) : null
  const lines: PricedLine[] = priced ? (pricing!.lines ?? []) : []
  const byRole = (role: string) => lines.filter((l) => l.role === role)
  const first = (role: string) => byRole(role)[0]
  const invLine = first('inverter')
  const batLine = first('battery')
  const invOpt = ch?.inverter_options?.find((o) => o.code === ch?.inverter_code)
  const batOpt = ch?.battery_options?.find((o) => o.code === ch?.battery_code)
  const invUnits = ch?.inverter_units ?? invLine?.qty ?? sizing.inverter.units
  const invKw = invOpt?.rating_kw ?? sizing.inverter.size_kw
  const gridJob = sizing.kind !== 'off_grid'
  const certs = (ch?.inverter_certifications ?? invLine?.certifications ?? '').trim()
  const gridInteractive = ch?.inverter_grid_interactive ?? invLine?.grid_interactive ?? null
  const batUnits = ch?.battery_units ?? batLine?.qty ?? 0
  const nominalKwh = batOpt && batUnits > 0 ? batOpt.rating_kwh * batUnits : sizing.battery.installed_kwh
  const withBattery = sizing.battery.installed_kwh > 0 || batUnits > 0
  const autonomy = (sizing.battery as SizingBlock['battery'] & BatteryAutonomy).days_of_autonomy ?? null
  const hy = sizing.hourly_year
  const offGrid = sizing.kind === 'off_grid'
  const warnings: Warning[] = [...sizing.warnings, ...(priced ? (pricing!.warnings ?? []).filter((w) => w.hard || DESIGN_CODES.has(w.code)) : [])]
  const pvNote = first('pv_cable_red')?.note ?? ''
  const pvRun = /x ([\d.]+) m/.exec(pvNote)?.[1]
  const acNote = first('thhn')?.note ?? ''
  const protection = ['dc_breaker', 'dc_spd', 'battery_breaker', 'battery_cable', 'ats', 'ac_breaker', 'ac_spd']
    .flatMap((role) => byRole(role))
    .map((l) => ({
      role: l.role,
      circuit:
        { dc_breaker: 'PV strings', dc_spd: 'DC side', battery_breaker: 'Battery', battery_cable: 'Battery', ats: 'Grid and loads', ac_breaker: 'AC side', ac_spd: 'AC side' }[l.role] ?? l.role,
      what: { dc_breaker: 'DC breaker', dc_spd: 'Surge protector (DC)', battery_breaker: 'Battery breaker', battery_cable: 'Battery cable', ats: 'Transfer switch', ac_breaker: 'AC breakers', ac_spd: 'Surge protectors (AC)' }[l.role] ?? l.role,
      line: l,
    }))

  return (
    <div>
      {warnings.map((w, i) => (
        <div key={w.code + i} className={`banner ${w.hard ? 'bad' : 'warn'}`} data-hard={w.hard ? '1' : undefined}>
          {w.message}
        </div>
      ))}

      <div className="kpis">
        <div className="kpi">
          <div className="label">Array</div>
          <div className="value">{n2(sizing.kwp)} kWp</div>
          <div className="sub">
            {sizing.panels} x {panelWp} W {panelName} · {KIND_LABEL[sizing.kind]}
            {sizing.roof_limited ? ` · roof limit (net-zero needs ${n1(sizing.target_kwp)} kWp)` : ` · roof allows up to ${n2(sizing.roof_max_kwp)} kWp`}
          </div>
        </div>
        <div className="kpi" data-testid="design-inverter">
          <div className="label">Inverter</div>
          <div className="value">
            {invUnits > 1 ? `${invUnits} × ` : ''}
            {invKw} kW
          </div>
          <div className="sub">
            {invLine ? `${invLine.code} ${invLine.name}` : priced ? 'no inverter in the list that fits' : 'model chosen once the panel is linked to the materials list'}
            {invLine && gridJob && (
              <>
                <br />
                {gridFlag(gridInteractive)} · certificate: {certs || 'none on file'}
              </>
            )}
            <br />
            needs {n1(sizing.inverter.required_kw)} kW, set by {sizing.inverter.binding}; peak {n1(sizing.inverter.peak_load_kw)} kW, surge {n1(sizing.inverter.surge_requirement_kw)} kW, PV {n1(sizing.inverter.pv_requirement_kw)} kW
          </div>
        </div>
        <div className="kpi" data-testid="design-battery">
          <div className="label">Battery</div>
          <div className="value">{withBattery ? `${n1(nominalKwh)} kWh` : 'none'}</div>
          <div className="sub">
            {withBattery ? (
              <>
                {n1(sizing.battery.usable_kwh)} kWh usable at {Math.round(sizing.battery.depth_of_discharge * 100)}% depth of discharge; {n1(sizing.battery.installed_kwh)} kWh nominal sized
                {batLine && (
                  <>
                    <br />
                    {qty(batLine.qty)} × {batLine.code} {batLine.name}
                    {ch?.battery_continuous_a ? ` · ${n0(ch.battery_continuous_a * batUnits)} A continuous` : ''}
                    {ch?.battery_current_a ? ` against ${n0(ch.battery_current_a * invUnits)} A the inverter can draw` : ''}
                  </>
                )}
              </>
            ) : (
              KIND_LABEL[sizing.kind]
            )}
          </div>
        </div>
        {withBattery && (
          <div className="kpi">
            <div className="label">Autonomy</div>
            <div className="value">{autonomy != null ? `${autonomy} ${autonomy === 1 ? 'evening' : 'evenings'}` : '-'}</div>
            <div className="sub">the battery carries this many evenings without sun (Pricing settings › System sizing)</div>
          </div>
        )}
        {hy?.available && sizing.kind !== 'net_metering' && (
          <div className="kpi">
            <div className="label">Hours the grid steps in</div>
            <div className="value">{n0(hy.loss_of_load_hours ?? 0)} h</div>
            <div className="sub">
              on {plural(hy.loss_of_load_days ?? 0, 'day')} over a real year of weather ({n0(hy.unserved_kwh ?? 0)} kWh)
            </div>
          </div>
        )}
        <div className="kpi">
          <div className="label">Consumption covered</div>
          <div className="value">{n0(sizing.coverage_pct)}%</div>
          <div className="sub">
            {n0(sizing.annual_consumption_kwh)} kWh/yr used, {n0(sizing.annual_production_kwh)} kWh/yr at the meter; {offGrid ? `${n0(sizing.annual_unserved_kwh)} kWh unserved` : `${n0(sizing.annual_import_kwh)} kWh from the grid, ${n0(sizing.annual_export_kwh)} exported`}
          </div>
        </div>
      </div>

      {ch ? (
        <div className="kpis">
          <div className="kpi" data-testid="design-strings">
            <div className="label">Strings</div>
            <div className="value">
              {ch.strings} × {ch.panels_per_string} panels
            </div>
            <div className="sub">
              {ch.string_voltage_v.toFixed(0)} V, {ch.string_current_a.toFixed(1)} A per string at Vmp
              {ch.rows?.length ? `; rows of ${ch.rows.map((r) => r.panels).join(', ')}` : ''}
            </div>
          </div>
          <div className="kpi" data-testid="design-pv-cable">
            <div className="label">PV cable</div>
            <div className="value">{ch.pv_gauge} mm²</div>
            <div className="sub">
              {pct1(ch.pv_drop)} voltage drop{pvRun ? ` over ${pvRun} m per string` : ''}; red and black, {ch.strings} runs
            </div>
          </div>
          <div className="kpi" data-testid="design-ac-cable">
            <div className="label">AC cable</div>
            <div className="value">{ch.ac_gauge} mm² THHN</div>
            <div className="sub">
              {ch.ac_current_a.toFixed(0)} A at rated output, {pct1(ch.ac_drop)} voltage drop{acNote ? `; ${acNote}` : ''}
            </div>
          </div>
        </div>
      ) : (
        <div className="banner warn">{pricing?.reason ?? 'Strings, cables and protection follow the bill of materials: link the panel to the materials list and Calculate.'}</div>
      )}

      {protection.length > 0 && (
        <>
          <h3>Protection</h3>
          <div className="table-wrap">
            <table className="protection">
              <thead>
                <tr>
                  <th>Circuit</th>
                  <th>Device</th>
                  <th>Item</th>
                  <th className="num">Qty</th>
                  <th>Basis</th>
                </tr>
              </thead>
              <tbody>
                {protection.map((p, i) => (
                  <tr key={p.role + i}>
                    <td>{p.circuit}</td>
                    <td>{p.what}</td>
                    <td>
                      {p.line.name || <span className="badge bad">not in list</span>} <span className="muted">{p.line.code}</span>
                    </td>
                    <td className="num">
                      {qty(p.line.qty)} {p.line.unit}
                    </td>
                    <td className="muted">{p.line.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {sizing.faces && sizing.faces.length > 0 && (
        <>
          <h3>Panels per face, best face first</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Face</th>
                  <th className="num">Panels used</th>
                  <th className="num">Positions</th>
                  <th>Rows from the eave</th>
                  <th className="num">kWp</th>
                  <th className="num">kWh per kWp at the panels</th>
                </tr>
              </thead>
              <tbody>
                {sizing.faces.map((f) => (
                  <tr key={f.face_id}>
                    <td>{f.name}</td>
                    <td className="num">{f.panels}</td>
                    <td className="num">{f.capacity}</td>
                    <td>{f.rows.join(', ') || '-'}</td>
                    <td className="num">{n2(f.kwp)}</td>
                    <td className="num">{n0(f.specific_yield_kwh_per_kwp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            Production is the sum over these panels, not the whole-roof blend; the plan drawings under Roof and production show which positions they take.
          </div>
        </>
      )}

      <h3>Energy balance</h3>
      <AuditResults audit={audit} sizing={sizing} panelName={panelName} panelWp={panelWp} tiles={false} />
    </div>
  )
}
