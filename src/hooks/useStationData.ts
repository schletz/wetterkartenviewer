import { useEffect, useState } from 'react'

/** Reload interval: the stations send every 10 min, so half of that keeps the current value at most 15 min old. */
const REFRESH_MS = 5 * 60 * 1000

/** Outcome of the latest request; `stationId` tells a stale outcome from the current one. */
export type StationDataState<T> = { stationId: string } & ({ data: T } | { error: string })

/**
 * Data of a station, loaded on mount and every `REFRESH_MS`.
 * Null while the first request for the station runs. A failed reload keeps the values of the last successful one
 * (their times show their age); only a station without any values shows the error.
 *
 * @param stationId the station; a change discards the data of the previous one
 * @param load requests the data as of a time; must be a stable function, every change starts a new request
 */
export function useStationData<T>(
  stationId: string,
  load: (stationId: string, now: Date, signal: AbortSignal) => Promise<T>,
): StationDataState<T> | null {
  const [state, setState] = useState<StationDataState<T> | null>(null)

  useEffect(() => {
    let controller = new AbortController()
    const reload = () => {
      controller.abort()
      controller = new AbortController()
      const { signal } = controller
      load(stationId, new Date(), signal)
        .then((data) => setState({ stationId, data }))
        .catch((error: unknown) => {
          if (signal.aborted) return
          const message = error instanceof Error ? error.message : String(error)
          setState((previous) => previous?.stationId === stationId && 'data' in previous
            ? previous
            : { stationId, error: message })
        })
    }
    reload()
    const timer = setInterval(reload, REFRESH_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [stationId, load])

  return state?.stationId === stationId ? state : null
}
