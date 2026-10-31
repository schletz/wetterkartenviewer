import { useState, type FormEvent } from 'react'
import { isValidLocation, type GeoLocation } from '../model/GeoLocation'
import styles from './LocationForm.module.css'

interface LocationFormProps {
  location: GeoLocation
  onSave: (location: GeoLocation) => void
}

/** Latitude and longitude input; saving reloads the meteograms and moves the chart marker. */
export default function LocationForm({ location, onSave }: LocationFormProps) {
  const [lat, setLat] = useState(String(location.lat))
  const [lon, setLon] = useState(String(location.lon))
  const draft = { lat: Number(lat), lon: Number(lon) }
  const valid = lat.trim() !== '' && lon.trim() !== '' && isValidLocation(draft)
  const changed = draft.lat !== location.lat || draft.lon !== location.lon

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (valid) onSave(draft)
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <label>
        Breite °N
        <input className={styles.input} type="number" step="0.01" min="-90" max="90"
          value={lat} onChange={(e) => setLat(e.target.value)} />
      </label>
      <label>
        Länge °E
        <input className={styles.input} type="number" step="0.01" min="-180" max="180"
          value={lon} onChange={(e) => setLon(e.target.value)} />
      </label>
      <button type="submit" disabled={!valid || !changed}>Ort übernehmen</button>
    </form>
  )
}
