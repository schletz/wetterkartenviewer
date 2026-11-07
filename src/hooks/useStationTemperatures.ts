import { useEffect, useState } from 'react'
import type { DayTemperatures } from '../model/stationTemperatures'
import { fetchDayTemperatures } from '../services/geosphereStations'

/** Reload interval: the stations send every 10 min, so half of that keeps the current value at most 15 min old. */
const REFRESH_MS = 5 * 60 * 1000

/** Outcome of the latest request; `stationId` tells a stale outcome from the current one. */
export type StationTemperaturesState = { stationId: string } & ({ temperatures: DayTemperatures } | { error: string })

/**
 * Temperatures of a station since 00 UTC, loaded on mount and every `REFRESH_MS`.
 * Null while the first request for the station runs. A failed reload keeps the values of the last successful one
 * (their times show their age); only a station without any values shows the error.
 */
export function useStationTemperatures(stationId: string): StationTemperaturesState | null {
  const [state, setState] = useState<StationTemperaturesState | null>(null)

  useEffect(() => {
    let controller = new AbortController()
    const load = () => {
      controller.abort()
      controller = new AbortController()
      const { signal } = controller
      fetchDayTemperatures(stationId, new Date(), signal)
        .then((temperatures) => setState({ stationId, temperatures }))
        .catch((error: unknown) => {
          if (signal.aborted) return
          const message = error instanceof Error ? error.message : String(error)
          setState((previous) => previous?.stationId === stationId && 'temperatures' in previous
            ? previous
            : { stationId, error: message })
        })
    }
    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [stationId])

  return state?.stationId === stationId ? state : null
}
