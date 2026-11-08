import { useEffect, useState, type PointerEvent } from 'react'
import { useStationData } from '../hooks/useStationData'
import { useStationList } from '../hooks/useStationList'
import { stationLabel, type WeatherStation } from '../model/WeatherStation'
import { fetchTemperatureSeries } from '../services/geosphereStations'
import StationChart from './StationChart'
import StationLegend from './StationLegend'
import StationMap from './StationMap'
import StationValueTable from './StationValueTable'
import styles from './StationViewer.module.css'

interface StationViewerProps {
  /** Station shown first; a click on the map changes the view, not this station. */
  initialStation: WeatherStation
  onClose: () => void
}

/** Text in place of data that is not there: the error, or a note while loading. */
function Status({ error }: { error?: string }) {
  return <div className={error ? styles.error : styles.status}>{error ?? 'wird geladen …'}</div>
}

/**
 * Window over the start page with the measurements of one station: the 10 min diagram, the hourly values and
 * a map of the stations around it. A click on the map shows that station here without touching the one stored
 * for the start page. Closes with the × button, Escape or a click beside it.
 */
export default function StationViewer({ initialStation, onClose }: StationViewerProps) {
  const [station, setStation] = useState(initialStation)
  const seriesState = useStationData(station.id, fetchTemperatureSeries)
  const series = seriesState && 'data' in seriesState ? seriesState.data : null
  const seriesError = seriesState && 'error' in seriesState ? seriesState.error : undefined
  const list = useStationList()

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // On press, not click: moving the map and letting go outside the window would count as a click on the backdrop.
  const pressBackdrop = (event: PointerEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onClose()
  }

  return (
    <div className={styles.backdrop} onPointerDown={pressBackdrop}>
      <div className={styles.window} role="dialog" aria-modal="true" aria-label={stationLabel(station)}>
        <div className={styles.titleBar}>
          <span>{stationLabel(station)} · {station.state}</span>
          <button className={styles.close} onClick={onClose} title="Schließen (Esc)">×</button>
        </div>
        <div className={styles.body}>
          <section className={styles.chart}>
            {series ? <StationChart stationName={station.name} series={series} /> : <Status error={seriesError} />}
          </section>
          <section className={styles.map}>
            {list && 'stations' in list
              ? <StationMap stations={list.stations} selectedId={station.id} onSelect={setStation} />
              : <Status error={list?.error} />}
          </section>
          <aside className={styles.side}>
            {series ? <StationValueTable key={station.id} samples={series.samples} /> : <div className={styles.grow} />}
            <StationLegend />
          </aside>
        </div>
      </div>
    </div>
  )
}
