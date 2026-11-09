/** Networks the app reads stations from. */
const STATION_SOURCE_IDS = ['geosphere', 'hungaromet'] as const

/** A network of stations; see `STATION_SOURCES`. */
export type StationSourceId = (typeof STATION_SOURCE_IDS)[number]

/** A measuring station, as kept in localStorage and shown above the diagrams. */
export interface WeatherStation {
  /** Network the station belongs to. */
  source: StationSourceId
  /** Station id within its network (synop number as a string, e.g. "11082"). */
  id: string
  /** Name as the network spells it, e.g. "GUMPOLDSKIRCHEN" or "Budapest Újpest". */
  name: string
  /** Federal state or county, e.g. "Niederösterreich" or "Pest". */
  state: string
  /** Station height in m above sea level. */
  altitude: number
}

/** A station with its position, as the station list of a network provides it. */
export interface LocatedStation extends WeatherStation {
  lat: number
  lon: number
}

/** True for an object that has every field of a station; guards values read from localStorage. */
export function isValidStation(value: unknown): value is WeatherStation {
  const station = value as Partial<WeatherStation> | null
  return typeof station === 'object' && station !== null
    && STATION_SOURCE_IDS.includes(station.source as StationSourceId)
    && typeof station.id === 'string' && station.id !== ''
    && typeof station.name === 'string'
    && typeof station.state === 'string'
    && typeof station.altitude === 'number' && Number.isFinite(station.altitude)
}

/** Identifies a station across all networks. */
export function stationKey(station: WeatherStation): string {
  return `${station.source}:${station.id}`
}

/**
 * Text that names a station in the picker, unique within the station list:
 * two stations share the name "NEUSIEDL AM SEE", but not their height.
 */
export function stationLabel(station: WeatherStation): string {
  return `${station.name} (${Math.round(station.altitude)} m)`
}
