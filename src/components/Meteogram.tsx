import { useEffect, useState } from 'react'
import type { GeoLocation } from '../model/GeoLocation'
import { fetchMeteogramUrl } from '../services/ecmwfMeteogram'
import styles from './Meteogram.module.css'

interface MeteogramProps {
  name: string
  location: GeoLocation
}

/** Outcome of one request; ``request`` tells a stale outcome from the current one. */
type Outcome = { request: string } & ({ url: string } | { error: string })

/** One ECMWF ENS meteogram, requested anew whenever the location changes. */
export default function Meteogram({ name, location }: MeteogramProps) {
  const [attempt, setAttempt] = useState(0)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const request = `${name} ${location.lat} ${location.lon} ${attempt}`

  useEffect(() => {
    const controller = new AbortController()
    fetchMeteogramUrl(name, location, controller.signal)
      .then((url) => setOutcome({ request, url }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setOutcome({ request, error: error instanceof Error ? error.message : String(error) })
        }
      })
    return () => controller.abort()
  }, [name, location, request])

  const current = outcome?.request === request ? outcome : null
  return (
    <figure className={styles.frame}>
      {current === null && <span className={styles.status}>{name} wird geladen …</span>}
      {current !== null && 'error' in current && (
        <span className={styles.status}>
          {current.error} <button onClick={() => setAttempt((a) => a + 1)}>Erneut laden</button>
        </span>
      )}
      {current !== null && 'url' in current && <img className={styles.image} src={current.url} alt={name} />}
    </figure>
  )
}
