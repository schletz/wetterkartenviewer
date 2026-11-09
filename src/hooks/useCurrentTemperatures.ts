import { useCallback, useRef, useState } from 'react'
import { stationKey, type StationSourceId, type WeatherStation } from '../model/WeatherStation'
import { STATION_SOURCES } from '../services/stationSources'

/**
 * Age from which a value is requested again. Slightly below the refresh interval of the map,
 * so a timer that fires a moment early does not skip a whole interval.
 */
const MAX_AGE_MS = 4 * 60 * 1000

export interface CurrentTemperatures {
  /** Latest value per `stationKey`; null if the station has none. A station not asked for yet has no entry. */
  temperatures: ReadonlyMap<string, number | null>
  /** Loads the stations whose value is missing or old, in one request per network. */
  request: (stations: WeatherStation[]) => void
}

/**
 * Current temperatures of a growing set of stations. The data hub allows 240 requests per hour,
 * so values already known are not asked for again while the map is moved.
 */
export function useCurrentTemperatures(): CurrentTemperatures {
  const [temperatures, setTemperatures] = useState<ReadonlyMap<string, number | null>>(new Map())
  const requestedAt = useRef(new Map<string, number>())

  const load = useCallback((source: StationSourceId, stations: WeatherStation[]) => {
    STATION_SOURCES[source].fetchCurrentTemperatures(stations.map((station) => station.id))
      .then((loaded) => setTemperatures((previous) => new Map([
        ...previous,
        ...stations.map((station): [string, number | null] => [stationKey(station), loaded.get(station.id) ?? null]),
      ])))
      .catch(() => {
        // The next map move tries again; until then a known value stays, an unknown one counts as unavailable.
        stations.forEach((station) => requestedAt.current.delete(stationKey(station)))
        setTemperatures((previous) => new Map([
          ...stations.map((station): [string, null] => [stationKey(station), null]),
          ...previous,
        ]))
      })
  }, [])

  const request = useCallback((stations: WeatherStation[]) => {
    const now = Date.now()
    const due = stations.filter((station) => now - (requestedAt.current.get(stationKey(station)) ?? 0) >= MAX_AGE_MS)
    // Set before the answer, so another map move in the meantime does not ask for the same stations.
    due.forEach((station) => requestedAt.current.set(stationKey(station), now))
    for (const source of new Set(due.map((station) => station.source))) {
      load(source, due.filter((station) => station.source === source))
    }
  }, [load])

  return { temperatures, request }
}
