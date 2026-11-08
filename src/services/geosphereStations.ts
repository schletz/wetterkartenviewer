import { seriesStart, type StationSeries } from '../model/stationSeries'
import { summarizeTemperatures, type DayTemperatures } from '../model/stationTemperatures'
import type { LocatedStation } from '../model/WeatherStation'

/**
 * GeoSphere Austria data hub, 10 min data of the TAWES stations (https://dataset.api.hub.geosphere.at/v1/docs/).
 * Public, no key, CORS open, at most 240 requests per hour and client; all times UTC.
 */
const DATASET_URL = 'https://dataset.api.hub.geosphere.at/v1/station'
const DATASET = 'tawes-v1-10min'

/** One entry of `stations` in the metadata response (only the fields the app reads). */
interface StationMetadata {
  id: string
  name: string
  state: string
  lat: number
  lon: number
  altitude: number
  is_active: boolean
}

/** Station response in GeoJSON: one feature per station, one array per parameter aligned with `timestamps`. */
interface StationDataResponse {
  timestamps: string[]
  features: {
    properties: {
      station: string
      parameters: Record<string, { data: (number | null)[] } | undefined>
    }
  }[]
}

async function fetchJson<T>(url: URL, signal: AbortSignal | undefined, what: string): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`${what} nicht verfügbar (HTTP ${response.status})`)
  return (await response.json()) as T
}

async function loadStations(): Promise<LocatedStation[]> {
  const url = new URL(`${DATASET_URL}/current/${DATASET}/metadata`)
  const metadata = await fetchJson<{ stations: StationMetadata[] }>(url, undefined, 'Stationsliste')
  return metadata.stations
    .filter((station) => station.is_active)
    .map(({ id, name, state, altitude, lat, lon }) => ({ id, name, state, altitude, lat, lon }))
    .sort((a, b) => a.name.localeCompare(b.name, 'de') || a.altitude - b.altitude)
}

let stationList: Promise<LocatedStation[]> | null = null

/**
 * Active TAWES stations, sorted by name (about 290, 87 KB of metadata).
 * Loaded once per page, a failed request is tried again by the next call.
 */
export function fetchStations(): Promise<LocatedStation[]> {
  stationList ??= loadStations().catch((error: unknown) => {
    stationList = null
    throw error
  })
  return stationList
}

/** `YYYY-MM-DDTHH:MM` in UTC, the time format of the data hub's `start` and `end`. */
function hubTime(time: Date): string {
  return time.toISOString().slice(0, 16)
}

/** Parameter arrays and time stamps of one station between two times. */
async function fetchHistorical(stationId: string, parameters: string, start: Date, end: Date, signal: AbortSignal) {
  const url = new URL(`${DATASET_URL}/historical/${DATASET}`)
  url.search = new URLSearchParams({
    parameters, station_ids: stationId, start: hubTime(start), end: hubTime(end),
  }).toString()
  const response = await fetchJson<StationDataResponse>(url, signal, 'Stationsdaten')
  const values = response.features[0]?.properties.parameters ?? {}
  return { timestamps: response.timestamps, series: (name: string) => values[name]?.data ?? [] }
}

/**
 * Current, lowest and highest air temperature of a station from 00 UTC of the current UTC day until `now`.
 *
 * @throws Error with a German message if the request fails.
 */
export async function fetchDayTemperatures(stationId: string, now: Date, signal: AbortSignal): Promise<DayTemperatures> {
  const midnight = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const { timestamps, series } = await fetchHistorical(stationId, 'TL,TLMAX,TLMIN', midnight, now, signal)
  return summarizeTemperatures(timestamps, series('TL'), series('TLMIN'), series('TLMAX'))
}

/**
 * 10 min air temperature of a station over the time span of the station viewer (see `seriesStart`).
 *
 * @throws Error with a German message if the request fails.
 */
export async function fetchTemperatureSeries(stationId: string, now: Date, signal: AbortSignal): Promise<StationSeries> {
  const start = seriesStart(now)
  const { timestamps, series } = await fetchHistorical(stationId, 'TL', start, now, signal)
  const values = series('TL')
  return {
    start,
    end: now,
    samples: timestamps.map((stamp, i) => ({ time: new Date(stamp), value: values[i] ?? null })),
  }
}

/**
 * Latest air temperature of several stations in one request (which counts once against the rate limit).
 * The response holds the last one or two 10 min slots; each station gets its newest value of them.
 * Every id must be a station of the dataset, an unknown one fails the whole request.
 *
 * @returns one entry per id, null for a station without a current value
 * @throws Error with a German message if the request fails.
 */
export async function fetchCurrentTemperatures(stationIds: string[]): Promise<Map<string, number | null>> {
  const url = new URL(`${DATASET_URL}/current/${DATASET}`)
  url.search = new URLSearchParams({ parameters: 'TL', station_ids: stationIds.join(',') }).toString()
  const response = await fetchJson<StationDataResponse>(url, undefined, 'Aktuelle Messwerte')
  const temperatures = new Map<string, number | null>(stationIds.map((id) => [id, null]))
  for (const { properties } of response.features) {
    const values = properties.parameters['TL']?.data ?? []
    temperatures.set(properties.station, values.findLast((value) => value !== null) ?? null)
  }
  return temperatures
}
