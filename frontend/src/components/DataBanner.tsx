import type { DataStatus } from '../types'

export default function DataBanner({ status }: { status: DataStatus | null }) {
  if (!status) return null
  if (!status.pvgis.available) {
    return (
      <div className="banner warn">
        Weather data is not downloaded yet. Ask whoever set up the server to run the one-time download (see README). Computing is off until then.
      </div>
    )
  }
  if (status.pvgis.synthetic) {
    return <div className="banner bad">Test weather data is in use. Results are not real and customer documents are disabled.</div>
  }
  return null
}
