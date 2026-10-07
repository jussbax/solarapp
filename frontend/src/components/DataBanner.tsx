import type { DataStatus } from '../types'

export default function DataBanner({ status }: { status: DataStatus | null }) {
  if (!status) return null
  if (!status.pvgis.available) {
    return (
      <div className="banner warn">
        Weather dataset not downloaded yet. Run the one-time download on the server (see README) before computing.
      </div>
    )
  }
  if (status.pvgis.synthetic) {
    return <div className="banner bad">SYNTHETIC TEST WEATHER DATA in use. Results are not real and the customer PDF is disabled.</div>
  }
  return null
}
