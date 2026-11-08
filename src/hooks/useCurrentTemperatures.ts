import { useCallback, useRef, useState } from 'react'
import { fetchCurrentTemperatures } from '../services/geosphereStations'

/**
 * Age from which a value is requested again. Slightly below the refresh interval of the map,
 * so a timer that fires a moment early does not skip a whole interval.
 */
const MAX_AGE_MS = 4 * 60 * 1000

export interface CurrentTemperatures {
  /** Latest value per requested station; null if the station has none. A station not asked for yet has no entry. */
  temperatures: ReadonlyMap<string, number | null>
  /** Loads the stations whose value is missing or old, all in one request. */
  request: (stationIds: string[]) => void
}

/**
 * Current temperatures of a growing set of stations. The data hub allows 240 requests per hour,
 * so values already known are not asked for again while the map is moved.
 */
export function useCurrentTemperatures(): CurrentTemperatures {
  const [temperatures, setTemperatures] = useState<ReadonlyMap<string, number | null>>(new Map())
  const requestedAt = useRef(new Map<string, number>())

  const request = useCallback((stationIds: string[]) => {
    const now = Date.now()
    const due = stationIds.filter((id) => now - (requestedAt.current.get(id) ?? 0) >= MAX_AGE_MS)
    if (due.length === 0) return
    // Set before the answer, so another map move in the meantime does not ask for the same stations.
    due.forEach((id) => requestedAt.current.set(id, now))
    fetchCurrentTemperatures(due)
      .then((loaded) => setTemperatures((previous) => new Map([...previous, ...loaded])))
      .catch(() => {
        // The next map move tries again; until then a known value stays, an unknown one counts as unavailable.
        due.forEach((id) => requestedAt.current.delete(id))
        setTemperatures((previous) => new Map([...due.map((id): [string, null] => [id, null]), ...previous]))
      })
  }, [])

  return { temperatures, request }
}
