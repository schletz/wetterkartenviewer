import { useState, type FormEvent } from 'react'
import { isValidLocation, type GeoLocation } from '../model/GeoLocation'
import { searchPlace } from '../services/placeSearch'
import styles from './LocationForm.module.css'

interface LocationFormProps {
  location: GeoLocation
  onSave: (location: GeoLocation) => void
}

/** Decimal places kept from a search hit: about 10 m, far finer than any model grid. */
const DECIMALS = 4

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
      <label>
        Ort
        <input className={styles.place} type="search" placeholder="z. B. Innsbruck"
          value={place} onChange={(e) => setPlace(e.target.value)} />
      </label>
      <label>
        Breite °N
        <input className={styles.input} type="number" step="any" min="-90" max="90"
          value={lat} onChange={(e) => setLat(e.target.value)} />
      </label>
      <label>
        Länge °E
        <input className={styles.input} type="number" step="any" min="-180" max="180"
          value={lon} onChange={(e) => setLon(e.target.value)} />
      </label>
      <button type="submit" disabled={searching || (!query && (!valid || !changed))}>
        {searching ? 'Suche …' : 'Ort übernehmen'}
      </button>
      {message && (
        <span className={message.error ? styles.error : styles.found} title={message.text}>{message.text}</span>
      )}
    </form>
  )
}
