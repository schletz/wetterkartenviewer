import { seriesStart } from '../model/stationSeries'
import { summarizeTemperatures } from '../model/stationTemperatures'
import type { LocatedStation, StationSourceId } from '../model/WeatherStation'
import type { StationDataSource } from './StationDataSource'

/** Where a station network speaks the API of the GeoSphere Austria data hub, and how it is named. */
export interface DataHubConfig {
  source: StationSourceId
  /** Base URL up to and including `/v1/station`. */
  stationUrl: string
  dataset: string
  name: string
  attribution: string
}

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

/** `YYYY-MM-DDTHH:MM` in UTC, the time format of the data hub's `start` and `end`. */
function hubTime(time: Date): string {
  return time.toISOString().slice(0, 16)
}

/**
 * Client of a service with the API of the GeoSphere Austria data hub (https://dataset.api.hub.geosphere.at/v1/docs/):
 * the hub itself, or the function in api/ that serves the Hungarian stations in the same form. All times UTC.
 */
export function createDataHubSource({ source, stationUrl, dataset, name, attribution }: DataHubConfig): StationDataSource {
  let stationList: Promise<LocatedStation[]> | null = null

  async function loadStations(): Promise<LocatedStation[]> {
    const url = new URL(`${stationUrl}/current/${dataset}/metadata`)
    const metadata = await fetchJson<{ stations: StationMetadata[] }>(url, undefined, 'Stationsliste')
    return metadata.stations
      .filter((station) => station.is_active)
      .map(({ id, name: stationName, state, altitude, lat, lon }) => ({ source, id, name: stationName, state, altitude, lat, lon }))
  }

  /** Parameter arrays and time stamps of one station between two times. */
  async function fetchHistorical(stationId: string, parameters: string, start: Date, end: Date, signal: AbortSignal) {
    const url = new URL(`${stationUrl}/historical/${dataset}`)
    url.search = new URLSearchParams({
      parameters, station_ids: stationId, start: hubTime(start), end: hubTime(end),
    }).toString()
    const response = await fetchJson<StationDataResponse>(url, signal, 'Stationsdaten')
    const values = response.features[0]?.properties.parameters ?? {}
    return { timestamps: response.timestamps, series: (parameter: string) => values[parameter]?.data ?? [] }
  }

  return {
    name,
    attribution,

    // A failed request is tried again by the next call.
    fetchStations() {
      stationList ??= loadStations().catch((error: unknown) => {
        stationList = null
        throw error
      })
      return stationList
    },

    async fetchDayTemperatures(stationId, now, signal) {
      const midnight = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
      const { timestamps, series } = await fetchHistorical(stationId, 'TL,TLMAX,TLMIN', midnight, now, signal)
      return summarizeTemperatures(timestamps, series('TL'), series('TLMIN'), series('TLMAX'))
    },

    async fetchTemperatureSeries(stationId, now, signal) {
      const start = seriesStart(now)
      const { timestamps, series } = await fetchHistorical(stationId, 'TL', start, now, signal)
      const values = series('TL')
      return {
        start,
        end: now,
        samples: timestamps.map((stamp, i) => ({ time: new Date(stamp), value: values[i] ?? null })),
      }
    },

    // The response holds the last one or two 10 min slots; each station gets its newest value of them.
    async fetchCurrentTemperatures(stationIds) {
      const url = new URL(`${stationUrl}/current/${dataset}`)
      url.search = new URLSearchParams({ parameters: 'TL', station_ids: stationIds.join(',') }).toString()
      const response = await fetchJson<StationDataResponse>(url, undefined, 'Aktuelle Messwerte')
      const temperatures = new Map<string, number | null>(stationIds.map((id) => [id, null]))
      for (const { properties } of response.features) {
        const values = properties.parameters['TL']?.data ?? []
        temperatures.set(properties.station, values.findLast((value) => value !== null) ?? null)
      }
      return temperatures
    },
  }
}
