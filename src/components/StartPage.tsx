import { viewerConfig } from '../config/viewerConfig'
import type { GeoLocation } from '../model/GeoLocation'
import LocationForm from './LocationForm'
import Meteogram from './Meteogram'
import styles from './StartPage.module.css'

interface StartPageProps {
  location: GeoLocation
  onLocationChange: (location: GeoLocation) => void
  onOpenMaps: () => void
}

/** ECMWF ENS meteograms for the stored location and the entry to the charts. */
export default function StartPage({ location, onLocationChange, onOpenMaps }: StartPageProps) {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Wetterkartenviewer</h1>
        <LocationForm location={location} onSave={onLocationChange} />
        <button className={styles.open} onClick={onOpenMaps}>Zu den Karten</button>
      </header>
      <section className={styles.meteograms}>
        {viewerConfig.meteograms.map((name) => (
          <Meteogram key={name} name={name} location={location} />
        ))}
      </section>
    </main>
  )
}
