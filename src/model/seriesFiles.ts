/**
 * The temperature series files of the start page as written by scripts/point_series.py.
 *
 * Every series is a flat list of whole multiples of `scale`, time-major (all
 * points of the first time, then all of the second ...) and as deltas along
 * time: the first time holds absolute values, every further one the change
 * since the previous time. `pointSeries` undoes this for one point.
 */
import type { GeoLocation } from './GeoLocation'

/** Box all files cover, in degrees. */
export interface Box {
  north: number
  south: number
  west: number
  east: number
}

/** Regular lat/lon grid; rows run north to south, so row j lies at lat0 - j * dlat. */
export interface RegularGrid {
  lat0: number
  lon0: number
  dlat: number
  dlon: number
  nj: number
  ni: number
}

export interface ClimateStatistics {
  /** Mean in °C. */
  mean: number[]
  /** Standard deviation in K. */
  std: number[]
}

/** ERA5 climatology for every day of the ECMWF run; each file holds only the kind the app draws. */
export interface ClimateBlock {
  /** Reference period, e.g. "1991–2020". */
  period: string
  grid: RegularGrid
  /** First day, YYYY-MM-DD (UTC). */
  first_day: string
  days: number
  /** ERA5 orography of every grid point, whole m; missing in files of older pipeline versions. */
  orog?: number[]
}

/** Climatology per analysis hour (t850.json). */
export interface TermClimateBlock extends ClimateBlock {
  /** Analysis hours (UTC) of `term`. */
  hours: number[]
  /** Per day and analysis hour, day-major. */
  term: ClimateStatistics
}

/** Climatology of the daily mean (t2m.json): mean and standard deviation of the daily means per day. */
export interface DailyClimateBlock extends ClimateBlock {
  daily: ClimateStatistics
}

/** One ECMWF field on the 0.1° grid of the box. */
export interface EcmwfBlock {
  /** Run, YYYYMMDDHH in UTC. */
  run: string
  /** Steps in hours after the run. */
  steps: number[]
  grid: RegularGrid
  /** Model orography of every grid point, m. */
  orog: number[]
}

/** ICON-D2 T2m on the cells of heights.json. */
export interface IconBlock {
  run: string
  steps: number[]
  /** Number of cells; must match heights.json. */
  cells: number
  t2m: number[]
}

export interface T850File {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { t850: number[] }
  climate: TermClimateBlock
}

export interface T2mFile {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { t2m: number[] }
  climate: DailyClimateBlock
  /** Missing if the pipeline had no ICON-D2 run. */
  icon?: IconBlock
}

/** The ICON-D2 cells of Austria: centre (deltas along the list, in coord_scale degrees) and model orography. */
export interface HeightsFile {
  version: string
  box: Box
  coord_scale: number
  cells: number
  lat: number[]
  lon: number[]
  /** Model orography in m. */
  hsurf: number[]
}

/** ECMWF 1000–500 hPa thickness in dam; no climatology. */
export interface ThicknessFile {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { thickness: number[] }
}

/** ECMWF T500 in °C; no climatology. */
export interface T500File {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { t500: number[] }
}

/** ECMWF relative humidity at 850 hPa in % (IFS definition, mixed phase below 0 °C); no climatology. */
export interface Rh850File {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { rh850: number[] }
}

/** ECMWF relative humidity at 700 hPa in % (IFS definition, mixed phase below 0 °C); no climatology. */
export interface Rh700File {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { rh700: number[] }
}

/** ECMWF equivalent potential temperature at 850 hPa in K (Bolton 1980, the derived field papt); no climatology. */
export interface ThetaE850File {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { thetae850: number[] }
}

/** A colour band of a chart scale: values from `lower` to `upper` get `colour` ("#rrggbb"). */
export type ColourBand = [lower: number, upper: number, colour: string]

/** ECMWF maximum 10 m gust in km/h with the colour bands of the wind10m chart; no climatology. */
export interface Gust10mFile {
  version: string
  box: Box
  scale: number
  /** Ascending and contiguous; values outside get the nearest band. */
  colours: ColourBand[]
  /** `hours`: length of the interval before each step the gust covers (1 h to T+90, 3 h to T+144, then 6 h). */
  ecmwf: EcmwfBlock & { gust10m: number[]; hours: number[] }
}

export interface SeriesFiles {
  t850: T850File
  t2m: T2mFile
  heights: HeightsFile
  /** Missing in manifests of older pipelines. */
  thickness?: ThicknessFile
  /** Missing in manifests of older pipelines. */
  t500?: T500File
  /** Missing in manifests of older pipelines. */
  rh850?: Rh850File
  /** Missing in manifests of older pipelines. */
  rh700?: Rh700File
  /** Missing in manifests of older pipelines. */
  thetae850?: ThetaE850File
  /** Missing in manifests of older pipelines. */
  gust10m?: Gust10mFile
}

/** Values of one point over time, in units of the file (°C or K). */
export function pointSeries(deltas: number[], points: number, index: number, scale: number): number[] {
  const values: number[] = []
  let whole = 0
  for (let offset = index; offset < deltas.length; offset += points) {
    whole += deltas[offset]
    // Rounded to the decimals of the scale, so 0.1 * 73 shows as 7.3.
    values.push(Math.round(whole * scale * 1e6) / 1e6)
  }
  return values
}

/** Running sums of a delta-coded list, scaled. */
export function cumulative(deltas: number[], scale: number): Float64Array {
  const values = new Float64Array(deltas.length)
  let whole = 0
  deltas.forEach((delta, i) => {
    whole += delta
    values[i] = whole * scale
  })
  return values
}

/** Index of the grid point nearest to a location, null outside the grid. */
export function gridIndex(grid: RegularGrid, location: GeoLocation): number | null {
  const row = Math.round((grid.lat0 - location.lat) / grid.dlat)
  const col = Math.round((location.lon - grid.lon0) / grid.dlon)
  if (row < 0 || row >= grid.nj || col < 0 || col >= grid.ni) return null
  return row * grid.ni + col
}

export function inBox(box: Box, location: GeoLocation): boolean {
  return location.lat <= box.north && location.lat >= box.south && location.lon >= box.west && location.lon <= box.east
}

/** Date of a run name YYYYMMDDHH (UTC). */
export function runTime(run: string): Date {
  return new Date(Date.UTC(+run.slice(0, 4), +run.slice(4, 6) - 1, +run.slice(6, 8), +run.slice(8, 10)))
}
