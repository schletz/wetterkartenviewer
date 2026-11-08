import { useEffect, useState } from 'react'
import type { LocatedStation } from '../model/WeatherStation'
import { fetchStations } from '../services/geosphereStations'

/** Station list request: the stations, or the German error text. */
export type StationList = { stations: LocatedStation[] } | { error: string }

/** The active TAWES stations; null while they load. */
export function useStationList(): StationList | null {
  const [list, setList] = useState<StationList | null>(null)

  useEffect(() => {
    let active = true
    fetchStations()
      .then((stations) => {
        if (active) setList({ stations })
      })
      .catch((error: unknown) => {
        if (active) setList({ error: error instanceof Error ? error.message : String(error) })
      })
    return () => {
      active = false
    }
  }, [])

  return list
}
