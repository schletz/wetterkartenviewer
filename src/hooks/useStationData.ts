import { useEffect, useState } from 'react'
import { stationKey, type WeatherStation } from '../model/WeatherStation'
import type { StationDataSource, StationLoader } from '../services/StationDataSource'
import { STATION_SOURCES } from '../services/stationSources'

/** Reload interval: the stations send every 10 min, so half of that keeps the current value at most 15 min old. */
const REFRESH_MS = 5 * 60 * 1000

/** Outcome of the latest request; `key` tells a stale outcome from the current one. */
export type StationDataState<T> = { key: string } & ({ data: T } | { error: string })

/**
 * Data of a station, loaded from its network on mount and every `REFRESH_MS`.
 * Null while the first request for the station runs. A failed reload keeps the values of the last successful one
 * (their times show their age); only a station without any values shows the error.
 *
 * @param station the station; a change discards the data of the previous one
 * @param loaderOf picks the kind of data from a network; must be a stable function
 */
export function useStationData<T>(
  station: WeatherStation,
  loaderOf: (source: StationDataSource) => StationLoader<T>,
): StationDataState<T> | null {
  const [state, setState] = useState<StationDataState<T> | null>(null)
  const key = stationKey(station)
  const { id, source } = station

  useEffect(() => {
    const load = loaderOf(STATION_SOURCES[source])
    let controller = new AbortController()
    const reload = () => {
      controller.abort()
      controller = new AbortController()
      const { signal } = controller
      load(id, new Date(), signal)
        .then((data) => setState({ key, data }))
        .catch((error: unknown) => {
          if (signal.aborted) return
          const message = error instanceof Error ? error.message : String(error)
          setState((previous) => previous?.key === key && 'data' in previous
            ? previous
            : { key, error: message })
        })
    }
    reload()
    const timer = setInterval(reload, REFRESH_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [key, id, source, loaderOf])

  return state?.key === key ? state : null
}
