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

/**
 * Opening zoom and the lowest one with values, about 100 m per pixel in Austria: a full HD window shows some
 * 40 stations at most, so a view needs few values. Below it the map only shows where the stations are.
 */
const VALUE_ZOOM = 10
/** All of Austria fits into the map area of the viewer. */
const MIN_ZOOM = 7
const MAX_ZOOM = 13
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
/** Share of the view loaded beyond each side, so a short move needs no request. */
const LOAD_MARGIN = 0.25
/** Wait after a move: several quick moves make one request (the data hub allows 240 per hour). */
const MOVE_DELAY_MS = 300
const REFRESH_MS = 5 * 60 * 1000
const MARKER_RADIUS = 7
/** Station without colour: below `VALUE_ZOOM`, or while its value is loading. Grey, so white stays „not available“. */
const PLAIN_RADIUS = 4
const PLAIN_FILL = '#8c96a0'
const BORDER = '#1d2228'

/**
 * Leaflet map with the stations around the selected one. From `VALUE_ZOOM` on, the points have the colour of their
 * current temperature and a name label, and the values follow the moved map. Below it every station is a small grey
 * point without a request, labelled only when selected. A click on a point selects the station; the map itself
 * stays where it is.
 */
export default function StationMap({ stations, selectedKey, onSelect }: StationMapProps) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markers = useRef(new Map<string, L.CircleMarker>())
  const { temperatures, request } = useCurrentTemperatures()
  const [zoom, setZoom] = useState(VALUE_ZOOM)
  // The map opens around the first station and is not moved by later selections.
  const [centre] = useState<L.LatLngTuple>(() => {
    const { lat, lon } = stations.find((station) => stationKey(station) === selectedKey) ?? DEFAULT_LOCATION
    return [lat, lon]
  })

  useEffect(() => {
    if (container.current === null) return
    const map = L.map(container.current, {
      center: centre,
      zoom: VALUE_ZOOM,
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      // The arrow keys belong to the page.
      keyboard: false,
    })
    L.tileLayer(TILE_URL, { attribution: ATTRIBUTION }).addTo(map)
    mapRef.current = map

    const requestVisible = () => {
      if (map.getZoom() < VALUE_ZOOM) return
      const bounds = map.getBounds().pad(LOAD_MARGIN)
      const visible = stations.filter((station) => bounds.contains([station.lat, station.lon]))
      if (visible.length > 0) request(visible)
    }
    let moveTimer: ReturnType<typeof setTimeout> | undefined
    // A zoom ends with a moveend too, so zooming in to `VALUE_ZOOM` loads the view.
    const onMove = () => {
      clearTimeout(moveTimer)
      moveTimer = setTimeout(requestVisible, MOVE_DELAY_MS)
    }
    const onZoom = () => setZoom(map.getZoom())
    map.on('moveend resize', onMove)
    map.on('zoomend', onZoom)
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
    const showValues = zoom >= VALUE_ZOOM
    for (const station of stations) {
      const key = stationKey(station)
      let marker = markers.current.get(key)
      if (marker === undefined) {
        marker = L.circleMarker([station.lat, station.lon], { color: BORDER, weight: 1.5, fillOpacity: 1 })
          .bindTooltip(station.name, {
            permanent: true, direction: 'top', offset: [0, -MARKER_RADIUS], className: styles.label,
          })
          .on('click', () => onSelect(station))
          .addTo(map)
        markers.current.set(key, marker)
      }
      const temperature = temperatures.get(key)
      if (showValues && temperature !== undefined) {
        marker.setRadius(MARKER_RADIUS)
        marker.setStyle({ fillColor: temperatureColour(temperature) })
      } else {
        marker.setRadius(PLAIN_RADIUS)
        marker.setStyle({ fillColor: PLAIN_FILL })
      }
      const label = marker.getTooltip()?.getElement()
      label?.classList.toggle(styles.selected, key === selectedKey)
      label?.classList.toggle(styles.hidden, !showValues && key !== selectedKey)
    }
  }, [stations, temperatures, selectedKey, onSelect, zoom])

  return <div ref={container} className={styles.map} />
}
