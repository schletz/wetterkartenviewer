import { useState, type FormEvent } from 'react'
import { isValidLocation, type GeoLocation } from '../model/GeoLocation'
import { searchPlace } from '../services/placeSearch'
import styles from './LocationForm.module.css'

interface LocationFormProps {
  location: GeoLocation
  onSave: (location: GeoLocation) => void
}

/** Decimal places kept from a search hit: about 1 km, finer than the 0.1° ECMWF grid, and fits the narrow fields. */
const DECIMALS = 2

/**
 * Place name or latitude and longitude; saving reloads the meteograms and moves the chart marker.
 * An entered place name takes precedence over the coordinates; its hit fills them in.
 */
export default function LocationForm({ location, onSave }: LocationFormProps) {
  const [place, setPlace] = useState('')
  const [lat, setLat] = useState(String(location.lat))
  const [lon, setLon] = useState(String(location.lon))
  const [searching, setSearching] = useState(false)
  const [message, setMessage] = useState<{ text: string, error: boolean } | null>(null)
  const draft = { lat: Number(lat), lon: Number(lon) }
  const valid = lat.trim() !== '' && lon.trim() !== '' && isValidLocation(draft)
  const changed = draft.lat !== location.lat || draft.lon !== location.lon
  const query = place.trim()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!query) {
      if (valid) onSave(draft)
      setMessage(null)
      return
    }
    setSearching(true)
    try {
      const found = await searchPlace(query)
      const rounded = { lat: Number(found.lat.toFixed(DECIMALS)), lon: Number(found.lon.toFixed(DECIMALS)) }
      setLat(String(rounded.lat))
      setLon(String(rounded.lon))
      setPlace('')
      setMessage({ text: found.name, error: false })
      onSave(rounded)
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : String(error), error: true })
    } finally {
      setSearching(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      {/* One row, also on a phone: the place field gives way, the coordinates keep their width. */}
      <div className={styles.row}>
        <label className={styles.placeLabel}>
          Ort
          <input className={styles.place} type="search" placeholder="z. B. Innsbruck"
            value={place} onChange={(e) => setPlace(e.target.value)} />
        </label>
        <label className={styles.coordinate}>
          <input className={styles.input} type="number" step="any" min="-90" max="90" aria-label="Breite"
            value={lat} onChange={(e) => setLat(e.target.value)} />
          °N
        </label>
        <label className={styles.coordinate}>
          <input className={styles.input} type="number" step="any" min="-180" max="180" aria-label="Länge"
            value={lon} onChange={(e) => setLon(e.target.value)} />
          °E
        </label>
        <button type="submit" disabled={searching || (!query && (!valid || !changed))}>
          {searching ? '…' : 'OK'}
        </button>
      </div>
      {message && (
        <span className={message.error ? styles.error : styles.found} title={message.text}>{message.text}</span>
      )}
    </form>
  )
}
