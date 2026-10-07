import { useEffect, useState } from 'react'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

const icon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

const PH_CENTER: [number, number] = [12.8, 121.8]

function ClickToSet({ onChange }: { onChange: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onChange(+e.latlng.lat.toFixed(6), +e.latlng.lng.toFixed(6))
    },
  })
  return null
}

function FlyTo({ lat, lon }: { lat: number | null; lon: number | null }) {
  const map = useMap()
  useEffect(() => {
    if (lat != null && lon != null) {
      const z = map.getZoom() < 14 ? 16 : map.getZoom()
      map.flyTo([lat, lon], z, { duration: 0.6 })
    }
  }, [lat, lon, map])
  return null
}

export default function MapPicker({
  lat,
  lon,
  onChange,
}: {
  lat: number | null
  lon: number | null
  onChange: (lat: number | null, lon: number | null) => void
}) {
  const [latText, setLatText] = useState(lat?.toString() ?? '')
  const [lonText, setLonText] = useState(lon?.toString() ?? '')
  const [geoError, setGeoError] = useState<string | null>(null)

  useEffect(() => {
    setLatText(lat?.toString() ?? '')
    setLonText(lon?.toString() ?? '')
  }, [lat, lon])

  const applyText = () => {
    const a = parseFloat(latText)
    const o = parseFloat(lonText)
    if (Number.isFinite(a) && Number.isFinite(o)) onChange(a, o)
  }

  const useGps = () => {
    setGeoError(null)
    if (!navigator.geolocation) {
      setGeoError('This browser has no location support.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => onChange(+p.coords.latitude.toFixed(6), +p.coords.longitude.toFixed(6)),
      (e) => setGeoError(e.message),
      { enableHighAccuracy: true, timeout: 15000 },
    )
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <div>
          <label>Latitude</label>
          <input value={latText} onChange={(e) => setLatText(e.target.value)} onBlur={applyText} inputMode="decimal" />
        </div>
        <div>
          <label>Longitude</label>
          <input value={lonText} onChange={(e) => setLonText(e.target.value)} onBlur={applyText} inputMode="decimal" />
        </div>
        <div className="narrow">
          <button type="button" onClick={useGps}>
            Use my location
          </button>
        </div>
      </div>
      {geoError && <div className="banner warn">{geoError}</div>}
      <div className="map">
        <MapContainer center={lat != null && lon != null ? [lat, lon] : PH_CENTER} zoom={lat != null ? 16 : 6} style={{ height: '100%' }}>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <ClickToSet onChange={onChange} />
          <FlyTo lat={lat} lon={lon} />
          {lat != null && lon != null && (
            <Marker
              position={[lat, lon]}
              icon={icon}
              draggable
              eventHandlers={{
                dragend: (e) => {
                  const p = (e.target as L.Marker).getLatLng()
                  onChange(+p.lat.toFixed(6), +p.lng.toFixed(6))
                },
              }}
            />
          )}
        </MapContainer>
      </div>
      <div className="muted" style={{ marginTop: 4 }}>
        Tap the map to drop the pin on the roof, or drag the pin. Satellite imagery is not available offline, so zoom in on the street map.
      </div>
    </div>
  )
}
