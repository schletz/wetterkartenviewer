import type { LocatedStation, StationSourceId } from '../model/WeatherStation'
import { createDataHubSource } from './dataHubSource'
import type { StationDataSource } from './StationDataSource'

/** Function in api/ on Azure; a local one can be set with VITE_HUNGARIAN_STATIONS_URL in `.env.local`. */
const HUNGARIAN_STATIONS_URL: string = import.meta.env.VITE_HUNGARIAN_STATIONS_URL as string | undefined
  ?? 'https://wetterkartenviewer-stations.azurewebsites.net/v1/station'

/** Every station network; the type makes a new id in `StationSourceId` a compile error here. */
export const STATION_SOURCES: Record<StationSourceId, StationDataSource> = {
  // Public, no key, CORS open, at most 240 requests per hour and client.
  geosphere: createDataHubSource({
    source: 'geosphere',
    stationUrl: 'https://dataset.api.hub.geosphere.at/v1/station',
    dataset: 'tawes-v1-10min',
    name: 'GeoSphere Austria',
    attribution: 'GeoSphere Austria',
  }),
  hungaromet: createDataHubSource({
    source: 'hungaromet',
    stationUrl: HUNGARIAN_STATIONS_URL,
    dataset: 'hungaromet-10min',
    name: 'HungaroMet',
    attribution: 'Database: Meteorological Database, HungaroMet Nonprofit Zrt., graphically reproduced data',
  }),
}

/**
 * The active stations of all networks, sorted by name. A network that cannot be reached is left out,
 * so the other one stays usable.
 *
 * @throws the error of the first network if none can be reached
 */
export async function fetchAllStations(): Promise<LocatedStation[]> {
  const results = await Promise.allSettled(Object.values(STATION_SOURCES).map((source) => source.fetchStations()))
  const loaded = results.filter((result) => result.status === 'fulfilled')
  if (loaded.length === 0) throw (results[0] as PromiseRejectedResult).reason
  return loaded
    .flatMap((result) => result.value)
    .sort((a, b) => a.name.localeCompare(b.name, 'de') || a.altitude - b.altitude)
}
