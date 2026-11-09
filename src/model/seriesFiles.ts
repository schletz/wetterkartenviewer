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
  /**
   * Per row the columns that hold data, as [start, length, start, length, ...]; the points of a file are numbered
   * row by row. Missing in files of older pipelines, which hold every point.
   */
  runs?: number[][]
}

/** A grid point that holds data: its number in the series of the file and its position. */
export interface GridPoint extends GeoLocation {
  index: number
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

/** The ICON-D2 cells of Austria and its margin: centre (deltas along the list, in coord_scale degrees) and model orography. */
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

/** ECMWF 2 m dew point in °C (over water); no climatology. */
export interface Td2mFile {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { td2m: number[] }
}

/** ECMWF 2 m wet-bulb temperature in °C (the derived field wbt); no climatology. */
export interface Tw2mFile {
  version: string
  box: Box
  scale: number
  ecmwf: EcmwfBlock & { tw2m: number[] }
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

/**
 * ECMWF precipitation in mm over the window before each step, as on the weather_summary chart (6 h, 3 h at T+3; up to
 * T+144 the windows of neighbouring steps overlap), with that chart's colour bands; no climatology.
 */
export interface Precip6hFile {
  version: string
  box: Box
  scale: number
  /** Ascending and contiguous; values outside get the nearest band. */
  colours: ColourBand[]
  /** Values below stay uncoloured, as on the chart. */
  transparent_below: number
  /**
   * `hours`: length of the window before each step. `ptype`: class of the precipitation in the window, 0 none (or
   * below `transparent_below`), 1 snow, 2 wet snow or rain and snow, 3 freezing rain or drizzle, ice pellets
   * (the symbol groups of the weather_summary chart), from the ECMWF ptype at every output step inside the window;
   * missing in files of older pipelines.
   */
  ecmwf: EcmwfBlock & { precip6h: number[]; hours: number[]; ptype?: number[] }
}

/** ECMWF total cloud cover in % at each step, with the colour bands of the weather_summary chart; no climatology. */
export interface TccFile {
  version: string
  box: Box
  scale: number
  /** Ascending and contiguous; values outside get the nearest band. */
  colours: ColourBand[]
  /** Values below stay uncoloured, as on the chart. */
  transparent_below: number
  ecmwf: EcmwfBlock & { tcc: number[] }
}

/** CHMI ALADIN T2m at the grid points of Hungary and its margin, with their position and model orography. */
export interface T2mAladinFile {
  version: string
  /** Run, YYYYMMDDHH in UTC. */
  run: string
  /** Steps in hours after the run. */
  steps: number[]
  scale: number
  /** Number of grid points: the length of one time in `t2m`. */
  points: number
  coord_scale: number
  /** Deltas along the list of points, in `coord_scale` degrees. */
  lat: number[]
  lon: number[]
  /** Model orography in m. */
  hsurf: number[]
  t2m: number[]
}

export interface SeriesFiles {
  t850: T850File
  t2m: T2mFile
  /** Without it the diagram has no ICON-D2 line. */
  heights?: HeightsFile
  /** Without it locations without ICON-D2 have no regional line. */
  t2m_aladin?: T2mAladinFile
  /** Missing in manifests of older pipelines. */
  td2m?: Td2mFile
  /** Missing in manifests of older pipelines. */
  tw2m?: Tw2mFile
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
  /** Missing in manifests of older pipelines. */
  precip6h?: Precip6hFile
  /** Missing in manifests of older pipelines. */
  tcc?: TccFile
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

/** Columns of a row that hold data, as [start, length, ...]. */
function rowRuns(grid: RegularGrid, row: number): number[] {
  return grid.runs?.[row] ?? [0, grid.ni]
}

/** Number of points a grid holds data for: the length of one time in its series. */
export function pointCount(grid: RegularGrid): number {
  let points = 0
  for (let row = 0; row < grid.nj; row++) {
    const runs = rowRuns(grid, row)
    for (let k = 1; k < runs.length; k += 2) points += runs[k]
  }
  return points
}

/** The grid point nearest to a location, null if that point lies outside the grid or holds no data. */
export function nearestGridPoint(grid: RegularGrid, location: GeoLocation): GridPoint | null {
  const row = Math.round((grid.lat0 - location.lat) / grid.dlat)
  const col = Math.round((location.lon - grid.lon0) / grid.dlon)
  if (row < 0 || row >= grid.nj || col < 0 || col >= grid.ni) return null
  // A file numbers only the points it holds, so the number is what the runs before this point add up to.
  let index = 0
  for (let j = 0; j <= row; j++) {
    const runs = rowRuns(grid, j)
    for (let k = 0; k < runs.length; k += 2) {
      const [start, length] = [runs[k], runs[k + 1]]
      if (j === row && col >= start && col < start + length) {
        return { index: index + col - start, lat: grid.lat0 - row * grid.dlat, lon: grid.lon0 + col * grid.dlon }
      }
      index += length
    }
  }
  return null
}

/** Date of a run name YYYYMMDDHH (UTC). */
export function runTime(run: string): Date {
  return new Date(Date.UTC(+run.slice(0, 4), +run.slice(4, 6) - 1, +run.slice(6, 8), +run.slice(8, 10)))
}
