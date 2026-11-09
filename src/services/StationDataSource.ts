import type { StationSeries } from '../model/stationSeries'
import type { DayTemperatures } from '../model/stationTemperatures'
import type { LocatedStation } from '../model/WeatherStation'

/** Requests one kind of data of a station as of a time. */
export type StationLoader<T> = (stationId: string, now: Date, signal: AbortSignal) => Promise<T>

/** A network of stations the app can read. The members are plain functions, safe to pass on without their object. */
export interface StationDataSource {
  /** Short name for the header, e.g. "HungaroMet". */
  readonly name: string
  /** Full citation of the source, as its terms of use ask for it. */
  readonly attribution: string
  /** The active stations, loaded once per page. */
  readonly fetchStations: () => Promise<LocatedStation[]>
  /** Current, lowest and highest air temperature from 00 UTC of the current UTC day until `now`. */
  readonly fetchDayTemperatures: StationLoader<DayTemperatures>
  /** 10 min air temperature over the time span of the station viewer (see `seriesStart`). */
  readonly fetchTemperatureSeries: StationLoader<StationSeries>
  /** Latest air temperature of several stations in one request; one entry per id, null for a station without value. */
  readonly fetchCurrentTemperatures: (stationIds: string[]) => Promise<Map<string, number | null>>
}
