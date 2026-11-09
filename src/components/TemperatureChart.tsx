import { useMemo } from 'react'
import { useSeriesFiles } from '../hooks/useSeriesFiles'
import type { GeoLocation } from '../model/GeoLocation'
import { TemperatureSeries } from '../model/TemperatureSeries'
import styles from './TemperatureChart.module.css'
import TemperatureDiagram from './TemperatureDiagram'

interface TemperatureChartProps {
  location: GeoLocation
}

/** T850 and T2m of ECMWF and of ICON-D2 (Austria) or CHMI ALADIN (Hungary) for the location; shown only where the ECMWF series have a point. */
export default function TemperatureChart({ location }: TemperatureChartProps) {
  const state = useSeriesFiles()
  // Decoding the cell coordinates once per file set, not on every location change.
  const series = useMemo(() => (state.status === 'ready' ? new TemperatureSeries(state.files) : null), [state])
  const temperatures = useMemo(() => series?.at(location) ?? null, [series, location])

  if (state.status === 'error') {
    return <figure className={styles.frame}><span className={styles.status}>Temperaturverlauf: {state.message}</span></figure>
  }
  if (temperatures === null) return null
  return (
    <figure className={styles.frame}>
      <TemperatureDiagram temperatures={temperatures} />
    </figure>
  )
}
