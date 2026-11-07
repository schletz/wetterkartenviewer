/** A TAWES station of GeoSphere Austria, as kept in localStorage and shown above the diagrams. */
export interface WeatherStation {
  /** Station id of the dataset (synop number as a string, e.g. "11082"). */
  id: string
  /** Name as GeoSphere spells it, in capitals (e.g. "GUMPOLDSKIRCHEN"). */
  name: string
  /** Federal state, e.g. "Niederösterreich". */
  state: string
  /** Station height in m above sea level. */
  altitude: number
}

/** True for an object that has every field of a station; guards values read from localStorage. */
export function isValidStation(value: unknown): value is WeatherStation {
  const station = value as Partial<WeatherStation> | null
  return typeof station === 'object' && station !== null
    && typeof station.id === 'string' && station.id !== ''
    && typeof station.name === 'string'
    && typeof station.state === 'string'
    && typeof station.altitude === 'number' && Number.isFinite(station.altitude)
}

/**
 * Text that names a station in the picker, unique within the station list:
 * two stations share the name "NEUSIEDL AM SEE", but not their height.
 */
export function stationLabel(station: WeatherStation): string {
  return `${station.name} (${Math.round(station.altitude)} m)`
}
