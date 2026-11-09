import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef, useState } from 'react'
import { useCurrentTemperatures } from '../hooks/useCurrentTemperatures'
import { DEFAULT_LOCATION } from '../model/GeoLocation'
import { temperatureColour } from '../model/temperatureBands'
import { stationKey, type LocatedStation } from '../model/WeatherStation'
import styles from './StationMap.module.css'

interface StationMapProps {
  /** All active stations. */
  stations: LocatedStation[]
  /** `stationKey` of the station shown in the viewer. */
  selectedKey: string
  onSelect: (station: LocatedStation) => void
}

/** Fixed zoom level, about 100 m per pixel in Austria: a full HD window shows some 40 stations at most. */
const ZOOM = 10
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
/** Share of the view loaded beyond each side, so a short move needs no request. */
const LOAD_MARGIN = 0.25
/** Wait after a move: several quick moves make one request (the data hub allows 240 per hour). */
const MOVE_DELAY_MS = 300
const REFRESH_MS = 5 * 60 * 1000
const MARKER_RADIUS = 7

/**
 * Leaflet map at a fixed zoom with the stations around the selected one as points in the colour of their current
 * temperature. A station appears once its value (or the lack of one) is known, so white always means „not available“.
 * The values follow the moved map. A click on a point selects the station; the map itself stays where it is.
 */
export default function StationMap({ stations, selectedKey, onSelect }: StationMapProps) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markers = useRef(new Map<string, L.CircleMarker>())
  const { temperatures, request } = useCurrentTemperatures()
  // The map opens around the first station and is not moved by later selections.
  const [centre] = useState<L.LatLngTuple>(() => {
    const { lat, lon } = stations.find((station) => stationKey(station) === selectedKey) ?? DEFAULT_LOCATION
    return [lat, lon]
  })

  useEffect(() => {
    if (container.current === null) return
    const map = L.map(container.current, {
      center: centre,
      zoom: ZOOM,
      minZoom: ZOOM,
      maxZoom: ZOOM,
      zoomControl: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      touchZoom: false,
      boxZoom: false,
      keyboard: false,
    })
    L.tileLayer(TILE_URL, { attribution: ATTRIBUTION }).addTo(map)
    mapRef.current = map

    const requestVisible = () => {
      const bounds = map.getBounds().pad(LOAD_MARGIN)
      const visible = stations.filter((station) => bounds.contains([station.lat, station.lon]))
      if (visible.length > 0) request(visible)
    }
    let moveTimer: ReturnType<typeof setTimeout> | undefined
    const onMove = () => {
      clearTimeout(moveTimer)
      moveTimer = setTimeout(requestVisible, MOVE_DELAY_MS)
    }
    map.on('moveend resize', onMove)
    requestVisible()
    const refreshTimer = setInterval(requestVisible, REFRESH_MS)

    const markersOfMap = markers.current
    return () => {
      clearTimeout(moveTimer)
      clearInterval(refreshTimer)
      map.remove()
      markersOfMap.clear()
      mapRef.current = null
    }
  }, [centre, request, stations])

  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    for (const station of stations) {
      const key = stationKey(station)
      const temperature = temperatures.get(key)
      if (temperature === undefined) continue
      let marker = markers.current.get(key)
      if (marker === undefined) {
        marker = L.circleMarker([station.lat, station.lon], {
          radius: MARKER_RADIUS, color: '#1d2228', weight: 1.5, fillOpacity: 1,
        })
          .bindTooltip(station.name, {
            permanent: true, direction: 'top', offset: [0, -MARKER_RADIUS], className: styles.label,
          })
          .on('click', () => onSelect(station))
          .addTo(map)
        markers.current.set(key, marker)
      }
      marker.setStyle({ fillColor: temperatureColour(temperature) })
      marker.getTooltip()?.getElement()?.classList.toggle(styles.selected, key === selectedKey)
    }
  }, [stations, temperatures, selectedKey, onSelect])

  return <div ref={container} className={styles.map} />
}
