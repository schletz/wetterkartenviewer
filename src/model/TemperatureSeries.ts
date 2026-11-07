import type { GeoLocation } from './GeoLocation'
import {
  cumulative, gridIndex, inBox, pointSeries, runTime,
  type ColourBand, type DailyClimateBlock, type EcmwfBlock, type RegularGrid, type SeriesFiles, type TermClimateBlock,
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
  /** ICON-D2 model orography of the nearest cell, m. */
  height: number
  t850: PointSeries
  /** ERA5 T850 climate at every valid time of `t850`, null where the climatology has no value. */
  climate850: (ClimatePoint | null)[]
  t2mEcmwf: PointSeries
  /** ERA5 climate of the daily mean T2m for every day of the run, from 00 UTC of its first day. */
  climate2m: DailyClimate[]
  /** ERA5 orography of the T2m climate point, m; undefined if the file has none. */
  climate2mHeight?: number
  /** Null if the files hold no ICON-D2 run. */
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
   * chart and the value below which it stays uncoloured; null without precip6h file.
   */
  precip6h: { series: PointSeries; colours: ColourBand[]; transparentBelow: number } | null
}

/** Picks the series of one location out of the files of the Austria box. */
export class TemperatureSeries {
  private readonly files: SeriesFiles
  private readonly cellLat: Float64Array
  private readonly cellLon: Float64Array

  constructor(files: SeriesFiles) {
    this.files = files
    const { lat, lon, coord_scale: scale } = files.heights
    this.cellLat = cumulative(lat, scale)
    this.cellLon = cumulative(lon, scale)
  }

  /** The series of the location; null outside Austria and its margin (no ICON cell near). */
  at(location: GeoLocation): LocationTemperatures | null {
    const { t850, t2m, td2m, tw2m, heights, thickness, t500, rh850, rh700, thetae850, gust10m, precip6h } = this.files
    if (!inBox(t850.box, location)) return null
    const cell = this.nearestCell(location)
    if (cell === null) return null

    const t850Series = ecmwfSeries(t850.ecmwf, t850.ecmwf.t850, t850.scale, location)
    const t2mSeries = ecmwfSeries(t2m.ecmwf, t2m.ecmwf.t2m, t2m.scale, location)
    const climate = climateAt(t850.climate, t850.scale, location, t850Series.values.map((p) => p.valid))
    const climate2m = dailyClimateAt(t2m.climate, t2m.scale, location)
    if (climate === null || climate2m === null) return null

    let t2mIcon: PointSeries | null = null
    const icon = t2m.icon
    // A heights.json of another cell selection does not fit the ICON series.
    if (icon !== undefined && icon.cells === heights.cells) {
      const start = runTime(icon.run).getTime()
      const values = pointSeries(icon.t2m, icon.cells, cell, t2m.scale)
      t2mIcon = {
        point: { lat: this.cellLat[cell], lon: this.cellLon[cell] },
        height: heights.hsurf[cell],
        values: values.map((value, i) => ({ valid: new Date(start + icon.steps[i] * HOUR_MS), value })),
      }
    }
    return {
      height: heights.hsurf[cell],
      t850: t850Series,
      climate850: climate.values,
      t2mEcmwf: t2mSeries,
      climate2m: climate2m.values,
      climate2mHeight: climate2m.height,
      t2mIcon,
      td2m: td2m === undefined ? null : ecmwfSeries(td2m.ecmwf, td2m.ecmwf.td2m, td2m.scale, location),
      tw2m: tw2m === undefined ? null : ecmwfSeries(tw2m.ecmwf, tw2m.ecmwf.tw2m, tw2m.scale, location),
      thickness: thickness === undefined
        ? null
        : ecmwfSeries(thickness.ecmwf, thickness.ecmwf.thickness, thickness.scale, location),
      t500: t500 === undefined ? null : ecmwfSeries(t500.ecmwf, t500.ecmwf.t500, t500.scale, location),
      rh850: rh850 === undefined ? null : ecmwfSeries(rh850.ecmwf, rh850.ecmwf.rh850, rh850.scale, location),
      rh700: rh700 === undefined ? null : ecmwfSeries(rh700.ecmwf, rh700.ecmwf.rh700, rh700.scale, location),
      thetae850: thetae850 === undefined
        ? null
        : ecmwfSeries(thetae850.ecmwf, thetae850.ecmwf.thetae850, thetae850.scale, location),
      gust10m: gust10m === undefined
        ? null
        : {
            series: ecmwfSeries(gust10m.ecmwf, gust10m.ecmwf.gust10m, gust10m.scale, location),
            hours: gust10m.ecmwf.hours,
            colours: gust10m.colours,
          },
      precip6h: precip6h === undefined
        ? null
        : {
            series: ecmwfSeries(precip6h.ecmwf, precip6h.ecmwf.precip6h, precip6h.scale, location),
            colours: precip6h.colours,
            transparentBelow: precip6h.transparent_below,
          },
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

/** Latitude and longitude of a grid point index. */
function gridPoint(grid: RegularGrid, index: number): GeoLocation {
  const row = Math.floor(index / grid.ni)
  return { lat: grid.lat0 - row * grid.dlat, lon: grid.lon0 + (index % grid.ni) * grid.dlon }
}

/** The series of the ECMWF grid point nearest to the location (the location lies in the box). */
function ecmwfSeries(block: EcmwfBlock, deltas: number[], scale: number, location: GeoLocation): PointSeries {
  const index = gridIndex(block.grid, location) ?? 0
  const start = runTime(block.run).getTime()
  const values = pointSeries(deltas, block.grid.ni * block.grid.nj, index, scale)
  return {
    point: gridPoint(block.grid, index),
    height: block.orog[index],
    values: values.map((value, i) => ({ valid: new Date(start + block.steps[i] * HOUR_MS), value })),
  }
}

/** Mean and standard deviation per analysis hour at the nearest ERA5 point, for each valid time, and its height. */
function climateAt(block: TermClimateBlock, scale: number, location: GeoLocation, valid: Date[]) {
  const index = gridIndex(block.grid, location)
  if (index === null) return null
  const points = block.grid.ni * block.grid.nj
  const mean = pointSeries(block.term.mean, points, index, scale)
  const std = pointSeries(block.term.std, points, index, scale)
  const firstDay = Date.parse(`${block.first_day}T00:00:00Z`)
  const values = valid.map((time): ClimatePoint | null => {
    const day = Math.floor((time.getTime() - firstDay) / DAY_MS)
    const hour = block.hours.indexOf(time.getUTCHours())
    if (day < 0 || day >= block.days || hour < 0 || time.getUTCMinutes() !== 0) return null
    const i = day * block.hours.length + hour
    return { mean: mean[i], std: std[i] }
  })
  return { height: block.orog?.[index], values }
}

/** Mean and standard deviation of the daily mean at the nearest ERA5 point for every day of the block, and its height. */
function dailyClimateAt(block: DailyClimateBlock, scale: number, location: GeoLocation) {
  const index = gridIndex(block.grid, location)
  if (index === null) return null
  const points = block.grid.ni * block.grid.nj
  const mean = pointSeries(block.daily.mean, points, index, scale)
  const std = pointSeries(block.daily.std, points, index, scale)
  const firstDay = Date.parse(`${block.first_day}T00:00:00Z`)
  const values = mean.map((m, i): DailyClimate => ({ day: new Date(firstDay + i * DAY_MS), mean: m, std: std[i] }))
  return { height: block.orog?.[index], values }
}
