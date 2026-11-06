import { useRef } from 'react'
import { useElementSize } from '../hooks/useElementSize'
import { anomalyPolygons, thresholdPolygons } from '../model/anomalyBands'
import { dailyMeans } from '../model/dailyMeans'
import { parcelLift } from '../model/moistAdiabat'
import type { GeoLocation } from '../model/GeoLocation'
import { placePanels, type LegendEntry, type PanelSpec, type TimeAxis } from '../model/panelLayout'
import type { ClimatePoint, DailyClimate, LocationTemperatures, ValuePoint } from '../model/TemperatureSeries'
import { TEMPERATURE_STEPS, THICKNESS_STEPS } from '../model/ValueAxis'
import styles from './TemperatureDiagram.module.css'
import TemperaturePanel from './TemperaturePanel'

// The SVG is drawn in pixels of its measured box, so the labels keep their size at any diagram size.
/** Room for the value labels left of the plots. */
const PLOT_LEFT = 34
const MARGIN_RIGHT = 10
const MARGIN_TOP = 2
const PANEL_GAP = 14
/** Anomaly layers k: areas beyond mean ± k σ, each adding the same shade (as in the synop skill). */
const SIGMA_STEPS = [0, 1, 2, 3] as const
/**
 * Largest height difference between the ECMWF and the ERA5 point, m, at which the T2m anomaly is drawn. Beyond it
 * (Alpine valleys and slopes) the climate refers to other ground and the anomaly would mostly show the lapse rate.
 */
const MAX_CLIMATE_HEIGHT_DIFFERENCE = 100
const TICK_HOURS = 6
const HOUR_MS = 3_600_000
const DAY_MS = 24 * HOUR_MS
const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
/**
 * The Showalter index shares the thickness panel without an axis of their own, around its middle: only its class
 * counts. 1 K spans at most THICKNESS_PER_KELVIN dam, the T850 scale of the synop skill's coupling
 * 544 dam + 1.6 dam/K × T850, so its swings stay about as large as those of the thickness; less only when the
 * largest would leave the plot.
 */
const THICKNESS_PER_KELVIN = 1.6
/**
 * Showalter classes, K, each layer shading darker like the σ layers of T850: above 0 stable (+1…+3 showers
 * possible, above +3 no convection from 850 hPa), below 0 thunderstorms possible (−3…−6 strong ones, below −6
 * severe weather potential). Values between −2 and −3 count to the first class.
 */
const SHOWALTER_STABLE = [0, 1, 3] as const
const SHOWALTER_UNSTABLE = [0, -3, -6] as const

interface TemperatureDiagramProps {
  temperatures: LocationTemperatures
}

const decimals = (value: number, digits: number) =>
  value.toLocaleString('de-AT', { minimumFractionDigits: digits, maximumFractionDigits: digits })

/** "+3", "0", "−3": a whole number with its sign. */
const signed = (value: number) => (value > 0 ? `+${value}` : value < 0 ? `−${-value}` : '0')

/** "48,20° N, 16,40° O, 180 m ü. A." */
function pointLabel(point: GeoLocation, height?: number): string {
  const position = `${decimals(point.lat, 2)}° N, ${decimals(point.lon, 2)}° O`
  return height === undefined ? position : `${position}, ${height} m ü. A.`
}

/** Tooltip parts of a value against its climate: "Ø 4,1 °C", "+1,2 σ"; none without climate. */
function climateParts(value: number, climate: ClimatePoint | null): string[] {
  if (climate === null) return []
  const parts = [`Ø ${decimals(climate.mean, 1)} °C`]
  if (climate.std > 0) {
    const sigma = (value - climate.mean) / climate.std
    parts.push(`${sigma >= 0 ? '+' : ''}${decimals(sigma, 1)} σ`)
  }
  return parts
}

/** "Mo 2.11. 06 UTC" */
function timeLabel(time: Date): string {
  return `${WEEKDAYS[time.getUTCDay()]} ${time.getUTCDate()}.${time.getUTCMonth() + 1}. ${String(time.getUTCHours()).padStart(2, '0')} UTC`
}

/**
 * Meteogram of T2m (ECMWF and ICON-D2) with the anomaly of the ECMWF daily mean against the ERA5 climate of the
 * daily mean as bars per day and the ECMWF 10 m gusts as a colour bar, T850 (ECMWF) with its anomaly against the
 * ERA5 climate, the ECMWF 1000–500 hPa thickness with the Showalter index of a parcel lifted from 850 hPa with its dew point from
 * RH850 as layered areas around the middle of its axis, blue above (stable), red below (unstable), and RH700 as a
 * line spanning the axis from 0 to 100 %, in panels one below the other like the ENS meteograms. Fills its parent.
 */
export default function TemperatureDiagram({ temperatures }: TemperatureDiagramProps) {
  const box = useRef<HTMLDivElement>(null)
  const size = useElementSize(box)
  const { t850, climate850, t2mEcmwf, climate2m, t2mIcon, thickness, t500, rh850, rh700, gust10m } = temperatures

  const plotRight = size.width - MARGIN_RIGHT
  const start = t850.values[0].valid.getTime()
  const end = t850.values[t850.values.length - 1].valid.getTime()
  const x = (time: Date | number) => PLOT_LEFT + ((+time - start) / (end - start)) * (plotRight - PLOT_LEFT)
  // ICON-D2 points outside the ECMWF range are dropped.
  const icon = t2mIcon?.values.filter((p) => +p.valid >= start && +p.valid <= end) ?? []

  // Days from 00 UTC of the first valid time; ticks every TICK_HOURS.
  const firstDay = Math.floor(start / (24 * HOUR_MS)) * 24 * HOUR_MS
  const days: number[] = []
  for (let day = firstDay; day <= end; day += 24 * HOUR_MS) days.push(day)
  const ticks: number[] = []
  for (let tick = firstDay; tick <= end; tick += TICK_HOURS * HOUR_MS) if (tick >= start) ticks.push(tick)
  const time: TimeAxis = { start, end, days, ticks, x }

  /** Climate mean as a line and the anomaly areas of a series whose climate is given per valid time. */
  const anomaly = (values: ValuePoint[], climate: (ClimatePoint | null)[]) => ({
    line: values.map((p, i) => {
      const c = climate[i]
      return c === null ? null : { valid: p.valid, value: c.mean }
    }),
    bands: anomalyPolygons(values.map((p, i) => {
      const c = climate[i]
      return c === null ? null : { x: x(p.valid), value: p.value, mean: c.mean, std: c.std }
    }), SIGMA_STEPS),
  })
  /**
   * Climate of the daily mean as a step line over every day and bars from it to the daily mean of the series, layered
   * by σ like the anomaly areas; days without a complete daily mean get no bar.
   */
  const dailyAnomaly = (values: ValuePoint[], climate: DailyClimate[]) => {
    const means = new Map(dailyMeans(values).map((p) => [+p.valid, p.value]))
    // End of one day and start of the next share their x, so the line steps vertically at 00 UTC.
    const line = climate.flatMap((c) => [{ valid: c.day, value: c.mean }, { valid: new Date(+c.day + DAY_MS), value: c.mean }])
    const bands = anomalyPolygons(climate.flatMap((c) => {
      const value = means.get(+c.day)
      if (value === undefined) return []
      const point = { value, mean: c.mean, std: c.std }
      // Two points per day give a rectangle; null keeps neighbouring days apart.
      return [{ x: x(c.day), ...point }, { x: x(+c.day + DAY_MS), ...point }, null]
    }), SIGMA_STEPS)
    return { line, bands, means }
  }
  const climateLabel = (point: GeoLocation, height?: number, prefix = '') =>
    `${prefix}Ø ${temperatures.period} ERA5 ${pointLabel(point, height)}`
  const climateLegend = (point: GeoLocation, height?: number, prefix = ''): LegendEntry => ({
    bands: { above: styles.warm, below: styles.cold, line: styles.climate },
    text: `${climateLabel(point, height, prefix)}, ±${SIGMA_STEPS.slice(1).join('/')} σ`,
  })
  const anomaly850 = anomaly(t850.values, climate850)
  const { climate2mPoint, climate2mHeight } = temperatures
  const show2m = climate2mHeight !== undefined
    && Math.abs(climate2mHeight - t2mEcmwf.height) <= MAX_CLIMATE_HEIGHT_DIFFERENCE
  // Without a comparable ERA5 point the T2m panel shows no climate at all: line, bars and tooltip would mislead alike.
  // Daily means, not terms: against a climate per term the daily cycle would dominate the anomaly.
  const shownClimate2m = show2m ? climate2m : []
  const anomaly2m = dailyAnomaly(t2mEcmwf.values, shownClimate2m)
  const climate2mByDay = new Map(shownClimate2m.map((c) => [+c.day, c]))
  const dailyPrefix = 'Tagesmittel, '
  const legend2m: LegendEntry = show2m
    ? climateLegend(climate2mPoint, climate2mHeight, dailyPrefix)
    : {
        note: true,
        text: `${climateLabel(climate2mPoint, climate2mHeight, dailyPrefix)}: ${climate2mHeight === undefined ? 'Höhe unbekannt' : `> ${MAX_CLIMATE_HEIGHT_DIFFERENCE} m Höhenunterschied`}, nicht gezeigt`,
      }
  // Vertical totals and the parcel reference only at valid times with T500 and RH850: either is worthless without
  // the other.
  const hasTotals = t500 !== null && rh850 !== null
  const t500ByTime = new Map(t500?.values.map((p) => [+p.valid, p.value]) ?? [])
  const rh850ByTime = new Map(rh850?.values.map((p) => [+p.valid, p.value]) ?? [])
  const parcels = t850.values.map((p) => {
    const rh = rh850ByTime.get(+p.valid)
    return rh === undefined ? null : parcelLift(p.value, rh)
  })
  const pairs = t850.values.map((p, i) => {
    const upper = t500ByTime.get(+p.valid)
    const parcel = parcels[i]
    return upper === undefined || parcel === null ? null : { valid: p.valid, totals: p.value - upper, parcel }
  })
  // Showalter index = parcel totals − VT: below zero the parcel is warmer than T500 at 500 hPa (unstable).
  const showalter = pairs.map((q) => q && { x: x(q.valid), value: q.parcel.totals - q.totals })
  const showalterBands = thresholdPolygons(showalter, SHOWALTER_STABLE, SHOWALTER_UNSTABLE)
  const extent = Math.max(0, ...showalter.map((q) => (q === null ? 0 : Math.abs(q.value))))
  // Stable (above zero) blue, unstable red: the reverse of the T850 anomaly colours.
  const showalterClasses = { above: styles.cold, below: styles.warm, line: styles.parcel }

  const panels: PanelSpec[] = [
    {
      key: 't2m',
      title: ['Temperatur in 2 m (°C)',
        ...(gust10m === null ? [] : ['Böen in 10 m (km/h)'])].join(', '),
      legend: [
        { line: styles.t2mEcmwf, text: `ECMWF ${pointLabel(t2mEcmwf.point, t2mEcmwf.height)}` },
        ...(t2mIcon === null ? [] : [{ line: styles.t2mIcon, text: `ICON-D2 ${pointLabel(t2mIcon.point, t2mIcon.height)}` }]),
        // The bars are the anomaly of the ECMWF daily mean.
        legend2m,
        // The bands of the wind10m chart, so a colour means the same speed in the diagram and on the map.
        ...(gust10m === null ? [] : [{ colours: gust10m.colours, text: 'ECMWF Böen, Stufen = Beaufort 0–1 … 12' }]),
      ],
      // Climate mean first, so the T2m lines lie on top of them; the bars lie below all lines.
      lines: [
        { values: anomaly2m.line, className: styles.climate },
        { values: t2mEcmwf.values, className: styles.t2mEcmwf },
        ...(icon.length > 0 ? [{ values: icon, className: styles.t2mIcon }] : []),
      ],
      bands: anomaly2m.bands,
      ...(gust10m === null ? {} : { colourBar: { values: gust10m.series.values, colours: gust10m.colours } }),
      steps: TEMPERATURE_STEPS,
      weight: 1,
    },
    {
      key: 't850',
      title: 'Temperatur in 850 hPa (°C)',
      legend: [
        { line: styles.t850, text: `ECMWF ${pointLabel(t850.point, t850.height)}` },
        climateLegend(temperatures.climatePoint),
      ],
      lines: [
        { values: anomaly850.line, className: styles.climate },
        { values: t850.values, className: styles.t850 },
      ],
      bands: anomaly850.bands,
      steps: TEMPERATURE_STEPS,
      weight: 1,
    },
    ...(thickness === null ? [] : [{
      key: 'thickness',
      title: ['Schichtdicke 1000–500 hPa (dam)', ...(hasTotals ? ['Showalter-Index'] : []), ...(rh700 === null ? [] : ['RH 700 hPa'])].join(', '),
      legend: [
        { line: styles.thickness, text: `ECMWF ${pointLabel(thickness.point, thickness.height)}` },
        ...(!hasTotals ? [] : [
          {
            bands: showalterClasses,
            text: `Paket aus 850 hPa mit Taupunkt, blau > ${SHOWALTER_STABLE.map(signed).join('/')} K, rot < ${SHOWALTER_UNSTABLE.map(signed).join('/')} K`,
          },
        ]),
        ...(rh700 === null ? [] : [{ line: styles.rh700, text: 'ECMWF RH 700 hPa, Achse unten 0 %, oben 100 %' }]),
      ],
      lines: [{ values: thickness.values, className: styles.thickness }],
      ...(rh700 === null ? {} : { percentLines: [{ values: rh700.values, className: styles.rh700 }] }),
      ...(!hasTotals ? {} : {
        centred: { polygons: showalterBands, extent, maxScale: THICKNESS_PER_KELVIN, classes: showalterClasses },
      }),
      steps: THICKNESS_STEPS,
      weight: 1,
    }]),
  ]

  const placed = placePanels(panels, MARGIN_TOP, size.height, PANEL_GAP)

  const iconByTime = new Map(icon.map((p) => [+p.valid, p.value]))
  const ecmwfByTime = new Map(t2mEcmwf.values.map((p) => [+p.valid, p.value]))
  // Gust and the hours before the valid time it covers.
  const gustByTime = new Map(gust10m?.series.values.map((p, i) => [+p.valid, { value: p.value, hours: gust10m.hours[i] }]) ?? [])
  const thicknessByTime = new Map(thickness?.values.map((p) => [+p.valid, p.value]) ?? [])
  const rh700ByTime = new Map(rh700?.values.map((p) => [+p.valid, p.value]) ?? [])
  const columns = t850.values.map((p) => x(p.valid))
  const tooltip = (point: ValuePoint, i: number) => {
    const parts = [timeLabel(point.valid)]
    const ecmwf = ecmwfByTime.get(+point.valid)
    if (ecmwf !== undefined) parts.push(`T2m ECMWF ${decimals(ecmwf, 1)} °C`)
    // Daily mean of the UTC day of the step and its anomaly, the values of the bar below the column.
    const day = Math.floor(+point.valid / DAY_MS) * DAY_MS
    const dailyMean = anomaly2m.means.get(day)
    if (dailyMean !== undefined) {
      parts.push(`Tagesmittel ECMWF ${decimals(dailyMean, 1)} °C`, ...climateParts(dailyMean, climate2mByDay.get(day) ?? null))
    }
    const iconValue = iconByTime.get(+point.valid)
    if (iconValue !== undefined) parts.push(`T2m ICON-D2 ${decimals(iconValue, 1)} °C`)
    const gust = gustByTime.get(+point.valid)
    if (gust !== undefined) parts.push(`Böe 10 m ${decimals(gust.value, 0)} km/h (${gust.hours} h)`)
    parts.push(`T850 ${decimals(point.value, 1)} °C`, ...climateParts(point.value, climate850[i]))
    const thicknessValue = thicknessByTime.get(+point.valid)
    if (thicknessValue !== undefined) parts.push(`Z1000–500 ${decimals(thicknessValue, 1)} dam`)
    const upper = t500ByTime.get(+point.valid)
    if (upper !== undefined) parts.push(`T500 ${decimals(upper, 1)} °C`)
    const pair = pairs[i]
    if (pair !== null) parts.push(`VT ${decimals(pair.totals, 1)} K (Paket ${decimals(pair.parcel.totals, 1)} K)`)
    const parcel = parcels[i]
    const rh = rh850ByTime.get(+point.valid)
    if (parcel !== null && rh !== undefined) {
      parts.push(`Td850 ${decimals(parcel.dewPoint, 1)} °C (RH ${decimals(rh, 0)} %)`)
      parts.push(`LCL ${decimals(parcel.lclPressure, 0)} hPa`)
    }
    const rh700Value = rh700ByTime.get(+point.valid)
    if (rh700Value !== undefined) parts.push(`RH700 ${decimals(rh700Value, 0)} %`)
    if (pair !== null) {
      const index = pair.parcel.totals - pair.totals
      parts.push(`Showalter ${index >= 0 ? '+' : ''}${decimals(index, 1)} K`)
    }
    return parts.join(' · ')
  }

  return (
    <div ref={box} className={styles.diagram}>
      {size.width > 0 && size.height > 0 && (
        <svg className={styles.svg} viewBox={`0 0 ${size.width} ${size.height}`} role="img"
          aria-label="T2m von ECMWF und ICON-D2 mit Abweichung des Tagesmittels vom Klimamittel und Böen in 10 m von ECMWF, T850 von ECMWF mit Abweichung vom Klimamittel, Schichtdicke 1000–500 hPa, Showalter-Index eines Pakets aus 850 hPa mit Taupunkt, relative Feuchte in 700 hPa">
          {placed.map((p) => <TemperaturePanel key={p.panel.key} placed={p} time={time} left={PLOT_LEFT} right={plotRight} />)}
          {t850.values.map((point, i) => {
            // Each hover column reaches halfway to its neighbours, so the 3 h and 6 h steps cover the plots without gaps.
            const left = i === 0 ? PLOT_LEFT : (columns[i - 1] + columns[i]) / 2
            const right = i === columns.length - 1 ? plotRight : (columns[i] + columns[i + 1]) / 2
            return (
              <g key={+point.valid} className={styles.hit}>
                <title>{tooltip(point, i)}</title>
                {placed.map(({ panel, plotTop, plotBottom }) => (
                  <g key={panel.key}>
                    <rect x={left} y={plotTop} width={right - left} height={plotBottom - plotTop} />
                    <line className={styles.cross} x1={columns[i]} x2={columns[i]} y1={plotTop} y2={plotBottom} />
                  </g>
                ))}
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}
