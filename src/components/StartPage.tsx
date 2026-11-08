import { lazy, Suspense, useRef, useState } from 'react'
import { viewerConfig } from '../config/viewerConfig'
import { useEdgeScroll } from '../hooks/useEdgeScroll'
import type { GeoLocation } from '../model/GeoLocation'
import type { WeatherStation } from '../model/WeatherStation'
import LocationForm from './LocationForm'
import Meteogram from './Meteogram'
import StationPanel from './StationPanel'
import styles from './StartPage.module.css'
import TemperatureChart from './TemperatureChart'

/** Loaded on first use: it brings Leaflet along, which the start page itself does not need. */
const StationViewer = lazy(() => import('./StationViewer'))

interface StartPageProps {
  location: GeoLocation
  onLocationChange: (location: GeoLocation) => void
  onOpenMaps: () => void
}

/**
 * Temperature diagram (in Austria) and ECMWF ENS meteograms for the stored location, and the entry to the charts.
 * On wide screens the cells fill the window height in one row that scrolls with the mouse at its edges.
 */
export default function StartPage({ location, onLocationChange, onOpenMaps }: StartPageProps) {
  const strip = useRef<HTMLElement>(null)
  const [viewedStation, setViewedStation] = useState<WeatherStation | null>(null)
  // The row lies behind the open viewer and must not scroll with the mouse at the window edges.
  useEdgeScroll(strip, viewedStation === null)
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Wetterkartenviewer</h1>
        <LocationForm location={location} onSave={onLocationChange} />
        <StationPanel onOpenStation={setViewedStation} />
        <button className={styles.open} onClick={onOpenMaps}>Zu den Karten</button>
      </header>
      <section ref={strip} className={styles.meteograms}>
        <TemperatureChart location={location} />
        {viewerConfig.meteograms.map((name) => (
          <Meteogram key={name} name={name} location={location} />
        ))}
      </section>
      {viewedStation && (
        <Suspense fallback={null}>
          <StationViewer initialStation={viewedStation} onClose={() => setViewedStation(null)} />
        </Suspense>
      )}
    </main>
  )
}
