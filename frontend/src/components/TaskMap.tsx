import { MapContainer, TileLayer, Marker, Polyline, Circle, Popup, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import L from 'leaflet'
import { TaskTurnpointOut, BarrelOut } from '../services/api'

// Fix default Leaflet marker icons broken by Vite
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

interface Props {
  turnpoints: TaskTurnpointOut[]
  barrels: BarrelOut[]
}

const BARREL_COLORS = [
  '#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed',
  '#0891b2', '#be185d', '#15803d',
]

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length > 0) {
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40] })
    }
  }, [map, points])
  return null
}

export default function TaskMap({ turnpoints, barrels }: Props) {
  const sorted = [...turnpoints].sort((a, b) => a.order - b.order)
  const pts: [number, number][] = sorted.map(t => [t.turnpoint.lat, t.turnpoint.lon])

  // Group barrels by radius for colour coding
  const uniqueRadii = [...new Set(barrels.map(b => b.barrel_radius_km))].sort((a, b) => b - a)

  if (pts.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        Add turnpoints to see the map
      </div>
    )
  }

  return (
    <MapContainer center={pts[0]} zoom={9} className="h-full w-full rounded-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds points={pts} />

      {/* Task route */}
      <Polyline positions={pts} color="#1e40af" weight={2} dashArray="6 4" />

      {/* Barrel rings per handicap */}
      {barrels.map((b, i) => {
        const colorIdx = uniqueRadii.indexOf(b.barrel_radius_km)
        const color = BARREL_COLORS[colorIdx % BARREL_COLORS.length]
        return sorted.slice(1, -1).map(ttp => (
          <Circle
            key={`${b.pilot.id}-${ttp.turnpoint.id}`}
            center={[ttp.turnpoint.lat, ttp.turnpoint.lon]}
            radius={b.barrel_radius_km * 1000}
            color={color}
            weight={1}
            fillOpacity={0.04}
          />
        ))
      })}

      {/* TP markers */}
      {sorted.map((ttp, i) => {
        const label = i === 0 ? 'Start' : i === sorted.length - 1 ? 'Finish' : `TP${i}`
        return (
          <Marker key={ttp.turnpoint.id} position={[ttp.turnpoint.lat, ttp.turnpoint.lon]}>
            <Popup>{label}: {ttp.turnpoint.name}</Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}
