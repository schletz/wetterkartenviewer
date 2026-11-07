import { summarizeTemperatures, type DayTemperatures } from '../model/stationTemperatures'
import type { WeatherStation } from '../model/WeatherStation'

/**
 * GeoSphere Austria data hub, 10 min data of the TAWES stations (https://dataset.api.hub.geosphere.at/v1/docs/).
 * Public, no key, CORS open; all times UTC.
 */
const DATASET_URL = 'https://dataset.api.hub.geosphere.at/v1/station'
const DATASET = 'tawes-v1-10min'

/** One entry of `stations` in the metadata response (only the fields the app reads). */
interface StationMetadata {
  id: string
  name: string
  state: string
  altitude: number
  is_active: boolean
}

/** Station response in GeoJSON: one feature per station, one array per parameter aligned with `timestamps`. */
interface StationDataResponse {
  timestamps: string[]
  features: { properties: { parameters: Record<string, { data: (number | null)[] } | undefined> } }[]
}

async function fetchJson<T>(url: URL, signal: AbortSignal | undefined, what: string): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`${what} nicht verfügbar (HTTP ${response.status})`)
  return (await response.json()) as T
}

/** Active TAWES stations, sorted by name (about 290, 87 KB of metadata). */
export async function fetchStations(signal?: AbortSignal): Promise<WeatherStation[]> {
  const url = new URL(`${DATASET_URL}/current/${DATASET}/metadata`)
  const metadata = await fetchJson<{ stations: StationMetadata[] }>(url, signal, 'Stationsliste')
  return metadata.stations
    .filter((station) => station.is_active)
    .map(({ id, name, state, altitude }) => ({ id, name, state, altitude }))
    .sort((a, b) => a.name.localeCompare(b.name, 'de') || a.altitude - b.altitude)
}

/** `YYYY-MM-DDTHH:MM` in UTC, the time format of the data hub's `start` and `end`. */
function hubTime(time: Date): string {
  return time.toISOString().slice(0, 16)
}

/**
 * Current, lowest and highest air temperature of a station from 00 UTC of the current UTC day until `now`.
 *
 * @throws Error with a German message if the request fails.
 */
export async function fetchDayTemperatures(stationId: string, now: Date, signal?: AbortSignal): Promise<DayTemperatures> {
  const midnight = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const url = new URL(`${DATASET_URL}/historical/${DATASET}`)
  url.search = new URLSearchParams({
    parameters: 'TL,TLMAX,TLMIN', station_ids: stationId, start: hubTime(midnight), end: hubTime(now),
  }).toString()
  const response = await fetchJson<StationDataResponse>(url, signal, 'Stationsdaten')
  const parameters = response.features[0]?.properties.parameters ?? {}
  const series = (name: string) => parameters[name]?.data ?? []
  return summarizeTemperatures(response.timestamps, series('TL'), series('TLMIN'), series('TLMAX'))
}
