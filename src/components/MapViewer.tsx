import type { GeoLocation } from '../model/GeoLocation'
import { useChartIndex } from '../hooks/useChartIndex'
import ChartGrid from './ChartGrid'
import styles from './MapViewer.module.css'

interface MapViewerProps {
  location: GeoLocation
  onBack: () => void
}

/** Loads the manifest of the current run, then shows the chart grid. */
export default function MapViewer({ location, onBack }: MapViewerProps) {
  const state = useChartIndex()

  if (state.status === 'ready') return <ChartGrid index={state.index} location={location} onBack={onBack} />
  return (
    <main className={styles.message}>
      {state.status === 'loading' ? 'Lade Kartenverzeichnis …' : state.message}
    </main>
  )
}
