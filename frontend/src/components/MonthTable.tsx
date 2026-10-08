import { useNarrow } from './responsive'

export interface MonthRow {
  key: string
  /** The row label on the desk (months as columns). */
  label: string
  /** The column header on the phone (months as rows); the label when left out. */
  short?: string
  /** One formatted value per month. */
  values: string[]
  /** The year column (desk) or the last row (phone). */
  total?: string
  muted?: boolean
  bold?: boolean
  /** Left off the phone layout (months as rows), where every series is a column: the secondary series stay on the desk. */
  phoneHide?: boolean
}

/** A months-by-series table: months across the top on the desk, months down the side under 640 px so the phone
 * never shows a 14-column table sideways. The values arrive formatted. */
export default function MonthTable({ months, rows: allRows, firstHeader = 'Month' }: { months: string[]; rows: MonthRow[]; firstHeader?: string }) {
  const narrow = useNarrow()
  const cls = (r: MonthRow) => [r.muted ? 'muted' : '', r.bold ? 'bold' : ''].filter(Boolean).join(' ') || undefined
  const rows = narrow ? allRows.filter((r) => !r.phoneHide) : allRows
  if (!narrow) {
    return (
      <div className="table-wrap">
        <table className="month-table">
          <thead>
            <tr>
              <th>{firstHeader}</th>
              {months.map((m) => (
                <th key={m} className="num">
                  {m}
                </th>
              ))}
              <th className="num">Year</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className={cls(r)}>
                <td>{r.label}</td>
                {r.values.map((v, i) => (
                  <td key={i} className="num">
                    {v}
                  </td>
                ))}
                <td className="num">{r.total ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  const hasTotal = rows.some((r) => r.total != null)
  return (
    <div className="table-wrap">
      <table className="month-table months-as-rows">
        <thead>
          <tr>
            <th>{firstHeader}</th>
            {rows.map((r) => (
              <th key={r.key} className={`num ${r.muted ? 'muted' : ''}`}>
                {r.short ?? r.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {months.map((m, i) => (
            <tr key={m}>
              <td>{m}</td>
              {rows.map((r) => (
                <td key={r.key} className={`num ${r.muted ? 'muted' : ''} ${r.bold ? 'bold' : ''}`}>
                  {r.values[i] ?? ''}
                </td>
              ))}
            </tr>
          ))}
          {hasTotal && (
            <tr className="bold">
              <td>Year</td>
              {rows.map((r) => (
                <td key={r.key} className={`num ${r.muted ? 'muted' : ''}`}>
                  {r.total ?? ''}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
