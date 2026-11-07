import { useStationTemperatures } from '../hooks/useStationTemperatures'
import type { TemperatureReading } from '../model/stationTemperatures'
import { stationLabel, type WeatherStation } from '../model/WeatherStation'
import styles from './StationReadings.module.css'

interface StationReadingsProps {
  station: WeatherStation
  /** Forgets the station, so the picker shows again. */
  onClear: () => void
}

/** Local time of the browser, e.g. „19:20“. */
const TIME_FORMAT = new Intl.DateTimeFormat('de-AT', { hour: '2-digit', minute: '2-digit' })

const VALUE_FORMAT = new Intl.NumberFormat('de-AT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** One value with its local time; a dash while the series has none. */
function Reading({ label, reading, className }: { label: string, reading: TemperatureReading | null, className: string }) {
  return (
    <span className={styles.reading}>
      <span className={styles.caption}>{label}</span>
      <span className={className}>{reading ? `${VALUE_FORMAT.format(reading.value)} °C` : '–'}</span>
      {reading && <span className={styles.time}>{TIME_FORMAT.format(reading.time)}</span>}
    </span>
  )
}

/**
 * Current, lowest and highest air temperature of the chosen station since 00 UTC, refreshed every few minutes,
 * and a button that forgets the station.
 */
export default function StationReadings({ station, onClear }: StationReadingsProps) {
  const state = useStationTemperatures(station.id)
  const temperatures = state && 'temperatures' in state ? state.temperatures : null

  return (
    <div className={styles.panel}>
      <span className={styles.station} title={`${station.state}, Station ${station.id}`}>{stationLabel(station)}</span>
      {state === null && <span className={styles.status}>wird geladen …</span>}
      {state && 'error' in state && <span className={styles.error}>{state.error}</span>}
      {temperatures && (
        <>
          <Reading label="Aktuell" reading={temperatures.current} className={styles.current} />
          <Reading label="Min" reading={temperatures.min} className={styles.min} />
          <Reading label="Max" reading={temperatures.max} className={styles.max} />
        </>
      )}
      <button className={styles.clear} onClick={onClear}>Station wechseln</button>
    </div>
  )
}
