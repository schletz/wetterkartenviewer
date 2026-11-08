import type { GeoLocation } from './GeoLocation'
import {
  cumulative, nearestGridPoint, pointCount, pointSeries, runTime,
  type ColourBand, type DailyClimateBlock, type EcmwfBlock, type GridPoint, type SeriesFiles, type TermClimateBlock,
} from './seriesFiles'

/** An ICON cell centre is never farther from a location inside its cells than this (degrees of latitude). */
const MAX_CELL_DISTANCE = 0.03
const HOUR_MS = 3_600_000
const DAY_MS = 24 * HOUR_MS

export interface ValuePoint {
  valid: Date
  value: number
}

/** Climate of one valid time: mean in °C, standard deviation in K. */
export interface ClimatePoint {
  mean: number
  std: number
}

/** Climate of the daily mean of one UTC day: mean of the daily means in °C, their standard deviation in K. */
export interface DailyClimate extends ClimatePoint {
  /** 00 UTC of the day. */
  day: Date
}

/** A series and the grid point or cell centre it belongs to. */
export interface PointSeries {
  point: GeoLocation
  /** Model orography of the point, m. */
  height: number
  values: ValuePoint[]
}

/** Every series the start page draws for one location. */
export interface LocationTemperatures {
  t850: PointSeries
  /** ERA5 T850 climate at every valid time of `t850`, null where the climatology has no value. */
  climate850: (ClimatePoint | null)[]
  t2mEcmwf: PointSeries
  /** ERA5 climate of the daily mean T2m for every day of the run, from 00 UTC of its first day. */
  climate2m: DailyClimate[]
  /** ERA5 orography of the T2m climate point, m; undefined if the file has none. */
  climate2mHeight?: number
  /** Null if the files hold no ICON-D2 run or no ICON-D2 cell lies near the location. */
  t2mIcon: PointSeries | null
  /** ECMWF 2 m dew point in °C; null without td2m file. */
  td2m: PointSeries | null
  /** ECMWF 2 m wet-bulb temperature in °C; null without tw2m file. */
  tw2m: PointSeries | null
  /** ECMWF 1000–500 hPa thickness in dam; null without thickness file. */
  thickness: PointSeries | null
  /** ECMWF T500 in °C; null without T500 file. */
  t500: PointSeries | null
  /** ECMWF RH850 in %; null without RH850 file. */
  rh850: PointSeries | null
  /** ECMWF RH700 in %; null without RH700 file. */
  rh700: PointSeries | null
  /** ECMWF equivalent potential temperature at 850 hPa in K; null without θe file. */
  thetae850: PointSeries | null
  /**
   * ECMWF maximum 10 m gust in km/h, the hours before each value it covers and the colour bands of the wind10m
   * chart; null without gust10m file.
   */
  gust10m: { series: PointSeries; hours: number[]; colours: ColourBand[] } | null
  /**
   * ECMWF precipitation in mm over the 6 h before each step (3 h at T+3), the colour bands of the weather_summary
   * chart, the value below which it stays uncoloured and the class of its type per step (`Precip6hFile`); null
   * without precip6h file.
   */
  precip6h: { series: PointSeries; types: ValuePoint[]; colours: ColourBand[]; transparentBelow: number } | null
  /**
   * ECMWF total cloud cover in % at each step, the colour bands of the weather_summary chart and the value below which
   * it stays uncoloured; null without tcc file.
   */
  tcc: { series: PointSeries; colours: ColourBand[]; transparentBelow: number } | null
}

/** Picks the series of one location out of the files of the region (Austria and Hungary, ICON-D2 only Austria). */
export class TemperatureSeries {
  private readonly files: SeriesFiles
  private readonly cellLat: Float64Array
  private readonly cellLon: Float64Array

  constructor(files: SeriesFiles) {
    this.files = files
    const { heights } = files
    this.cellLat = heights === undefined ? new Float64Array(0) : cumulative(heights.lat, heights.coord_scale)
    this.cellLon = heights === undefined ? new Float64Array(0) : cumulative(heights.lon, heights.coord_scale)
  }

  /** The series of the location; null where the ECMWF files hold no point for it. */
  at(location: GeoLocation): LocationTemperatures | null {
    const { t850, t2m, td2m, tw2m, thickness, t500, rh850, rh700, thetae850, gust10m, precip6h, tcc } = this.files
    // All ECMWF files come from one grid and one selection of points.
    const point = nearestGridPoint(t850.ecmwf.grid, location)
    if (point === null) return null

    const t850Series = ecmwfSeries(t850.ecmwf, t850.ecmwf.t850, t850.scale, point)
    const t2mSeries = ecmwfSeries(t2m.ecmwf, t2m.ecmwf.t2m, t2m.scale, point)
    const climate = climateAt(t850.climate, t850.scale, location, t850Series.values.map((p) => p.valid))
    const climate2m = dailyClimateAt(t2m.climate, t2m.scale, location)
    if (climate === null || climate2m === null) return null

    return {
      t850: t850Series,
      climate850: climate.values,
      t2mEcmwf: t2mSeries,
      climate2m: climate2m.values,
      climate2mHeight: climate2m.height,
      t2mIcon: this.iconSeries(location),
      td2m: td2m === undefined ? null : ecmwfSeries(td2m.ecmwf, td2m.ecmwf.td2m, td2m.scale, point),
      tw2m: tw2m === undefined ? null : ecmwfSeries(tw2m.ecmwf, tw2m.ecmwf.tw2m, tw2m.scale, point),
      thickness: thickness === undefined
        ? null
        : ecmwfSeries(thickness.ecmwf, thickness.ecmwf.thickness, thickness.scale, point),
      t500: t500 === undefined ? null : ecmwfSeries(t500.ecmwf, t500.ecmwf.t500, t500.scale, point),
      rh850: rh850 === undefined ? null : ecmwfSeries(rh850.ecmwf, rh850.ecmwf.rh850, rh850.scale, point),
      rh700: rh700 === undefined ? null : ecmwfSeries(rh700.ecmwf, rh700.ecmwf.rh700, rh700.scale, point),
      thetae850: thetae850 === undefined
        ? null
        : ecmwfSeries(thetae850.ecmwf, thetae850.ecmwf.thetae850, thetae850.scale, point),
      gust10m: gust10m === undefined
        ? null
        : {
            series: ecmwfSeries(gust10m.ecmwf, gust10m.ecmwf.gust10m, gust10m.scale, point),
            hours: gust10m.ecmwf.hours,
            colours: gust10m.colours,
          },
      precip6h: precip6h === undefined
        ? null
        : {
            series: ecmwfSeries(precip6h.ecmwf, precip6h.ecmwf.precip6h, precip6h.scale, point),
            // Whole class numbers, not in units of the precipitation scale; older files have none.
            types: precip6h.ecmwf.ptype === undefined
              ? []
              : ecmwfSeries(precip6h.ecmwf, precip6h.ecmwf.ptype, 1, point).values,
            colours: precip6h.colours,
            transparentBelow: precip6h.transparent_below,
          },
      tcc: tcc === undefined
        ? null
        : {
            series: ecmwfSeries(tcc.ecmwf, tcc.ecmwf.tcc, tcc.scale, point),
            colours: tcc.colours,
            transparentBelow: tcc.transparent_below,
          },
    }
  }

  /** ICON-D2 T2m of the nearest cell; null without an ICON-D2 run or a cell within MAX_CELL_DISTANCE. */
  private iconSeries(location: GeoLocation): PointSeries | null {
    const { t2m: { icon, scale }, heights } = this.files
    // A heights.json of another cell selection does not fit the ICON series.
    if (icon === undefined || heights === undefined || icon.cells !== heights.cells) return null
    const cell = this.nearestCell(location)
    if (cell === null) return null
    const start = runTime(icon.run).getTime()
    return {
      point: { lat: this.cellLat[cell], lon: this.cellLon[cell] },
      height: heights.hsurf[cell],
      values: pointSeries(icon.t2m, icon.cells, cell, scale)
        .map((value, i) => ({ valid: new Date(start + icon.steps[i] * HOUR_MS), value })),
    }
  }

  /** Index of the nearest ICON cell, null if none lies within MAX_CELL_DISTANCE. */
  private nearestCell(location: GeoLocation): number | null {
    const shrink = Math.cos((location.lat * Math.PI) / 180)
    let best: number | null = null
    let bestDistance = MAX_CELL_DISTANCE ** 2
    for (let i = 0; i < this.cellLat.length; i++) {
      const distance = (this.cellLat[i] - location.lat) ** 2 + ((this.cellLon[i] - location.lon) * shrink) ** 2
      if (distance <= bestDistance) {
        best = i
        bestDistance = distance
      }
    }
    return best
  }
}

/** The series of an ECMWF grid point. */
function ecmwfSeries(block: EcmwfBlock, deltas: number[], scale: number, point: GridPoint): PointSeries {
  const start = runTime(block.run).getTime()
  const values = pointSeries(deltas, pointCount(block.grid), point.index, scale)
  return {
    point: { lat: point.lat, lon: point.lon },
    height: block.orog[point.index],
    values: values.map((value, i) => ({ valid: new Date(start + block.steps[i] * HOUR_MS), value })),
  }
}

/** Mean and standard deviation per analysis hour at the nearest ERA5 point, for each valid time, and its height. */
function climateAt(block: TermClimateBlock, scale: number, location: GeoLocation, valid: Date[]) {
  const point = nearestGridPoint(block.grid, location)
  if (point === null) return null
  const points = pointCount(block.grid)
  const mean = pointSeries(block.term.mean, points, point.index, scale)
  const std = pointSeries(block.term.std, points, point.index, scale)
  const firstDay = Date.parse(`${block.first_day}T00:00:00Z`)
  const values = valid.map((time): ClimatePoint | null => {
    const day = Math.floor((time.getTime() - firstDay) / DAY_MS)
    const hour = block.hours.indexOf(time.getUTCHours())
    if (day < 0 || day >= block.days || hour < 0 || time.getUTCMinutes() !== 0) return null
    const i = day * block.hours.length + hour
    return { mean: mean[i], std: std[i] }
  })
  return { height: block.orog?.[point.index], values }
}

/** Mean and standard deviation of the daily mean at the nearest ERA5 point for every day of the block, and its height. */
function dailyClimateAt(block: DailyClimateBlock, scale: number, location: GeoLocation) {
  const point = nearestGridPoint(block.grid, location)
  if (point === null) return null
  const points = pointCount(block.grid)
  const mean = pointSeries(block.daily.mean, points, point.index, scale)
  const std = pointSeries(block.daily.std, points, point.index, scale)
  const firstDay = Date.parse(`${block.first_day}T00:00:00Z`)
  const values = mean.map((m, i): DailyClimate => ({ day: new Date(firstDay + i * DAY_MS), mean: m, std: std[i] }))
  return { height: block.orog?.[point.index], values }
}
