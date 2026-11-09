import { useRef } from 'react'
import { useElementSize } from '../hooks/useElementSize'
import { anomalyPolygons, thresholdPolygons } from '../model/anomalyBands'
import { dailyMeans } from '../model/dailyMeans'
import { equivalentPotentialTemperature850, parcelLift, potentialTemperature850 } from '../model/moistAdiabat'
import type { GeoLocation } from '../model/GeoLocation'
import { placePanels, type BarMark, type LegendEntry, type PanelSpec, type ScaledLine, type TimeAxis } from '../model/panelLayout'
import type { ClimatePoint, DailyClimate, LocationTemperatures, ValuePoint } from '../model/TemperatureSeries'
import { TEMPERATURE_SCALE, THICKNESS_SCALE } from '../model/ValueAxis'
import { downloadSvg, EXPORT_SKIP } from '../services/svgExport'
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
/** RH700 spans the thickness axis: 0 % at its bottom, 100 % at its top. */
const PERCENT_RANGE = () => [0, 100] as const
/**
 * θe850 spans the T850 axis from the θe of dry air at its lowest to that of saturated air at its highest temperature:
 * the lowest and the highest θe air within the axis range can have, so the line never leaves the plot while T850
 * stays on it, and its scale follows from the axis alone.
 */
const THETA_E_RANGE = (min: number, max: number) =>
  [potentialTemperature850(min), equivalentPotentialTemperature850(max, 100)] as const

/**
 * Symbols of the precipitation classes of precip6h.json (1 snow, 2 wet snow or rain and snow, 3 freezing), those of
 * the weather_summary chart: white and orange asterisks with a dark halo, a red diamond.
 */
const PRECIP_TYPE_MARKS: Record<number, Omit<BarMark, 'valid'>> = {
  1: { shape: 'asterisk', className: styles.snow, haloClassName: styles.snowHalo },
  2: { shape: 'asterisk', className: styles.wetSnow, haloClassName: styles.wetSnowHalo },
  3: { shape: 'diamond', className: styles.freezing },
}

interface TemperatureDiagramProps {
  temperatures: LocationTemperatures
}

const decimals = (value: number, digits: number) =>
  value.toLocaleString('de-AT', { minimumFractionDigits: digits, maximumFractionDigits: digits })

/** "48,20° N, 16,40° O, 180 m ü. A." */
function pointLabel(point: GeoLocation, height?: number): string {
  const position = `${decimals(point.lat, 2)}° N, ${decimals(point.lon, 2)}° O`
  return height === undefined ? position : `${position}, ${height} m ü. A.`
}

/** "temperaturverlauf_48.20N_16.40E_2026110700.svg": location and first valid time (the ECMWF run). */
function exportFileName(point: GeoLocation, start: Date): string {
  const run = start.toISOString().slice(0, 13).replace(/\D/g, '')
  return `temperaturverlauf_${point.lat.toFixed(2)}N_${point.lon.toFixed(2)}E_${run}.svg`
}

/** "Mo 2.11. 06 UTC" */
function timeLabel(time: Date): string {
  return `${WEEKDAYS[time.getUTCDay()]} ${time.getUTCDate()}.${time.getUTCMonth() + 1}. ${String(time.getUTCHours()).padStart(2, '0')} UTC`
}

/**
 * Meteogram of T2m (ECMWF and a regional model: ICON-D2 where it has a cell, else CHMI ALADIN) with the ECMWF 2 m dew point and wet-bulb temperature, the anomaly of the
 * ECMWF daily mean against the ERA5 climate of the daily mean as bars per day and the ECMWF 10 m gusts as a colour bar, T850 (ECMWF) with its anomaly against the
 * ERA5 climate, θe850 as a line spanning the axis from the θe of dry air at its lowest to that of saturated air at
 * its highest temperature and the ECMWF precipitation per step as a colour bar with the ECMWF cloud cover in its dry blocks, the ECMWF 1000–500 hPa thickness with the Showalter index of a parcel lifted from 850 hPa with its dew point from
 * RH850 as layered areas around the middle of its axis, blue above (stable), red below (unstable), and RH700 as a
 * line spanning the axis from 0 to 100 %, in panels one below the other like the ENS meteograms. Fills its parent.
 */
export default function TemperatureDiagram({ temperatures }: TemperatureDiagramProps) {
  const box = useRef<HTMLDivElement>(null)
  const svg = useRef<SVGSVGElement>(null)
  const size = useElementSize(box)
  const {
    t850, climate850, t2mEcmwf, climate2m, t2mRegional, td2m, tw2m, thickness, t500, rh850, rh700, thetae850, gust10m,
    precip6h, tcc,
  } = temperatures

  const plotRight = size.width - MARGIN_RIGHT
  const start = t850.values[0].valid.getTime()
  const end = t850.values[t850.values.length - 1].valid.getTime()
  const x = (time: Date | number) => PLOT_LEFT + ((+time - start) / (end - start)) * (plotRight - PLOT_LEFT)
  // Points of the regional model outside the ECMWF range are dropped.
  const regional = t2mRegional?.values.filter((p) => +p.valid >= start && +p.valid <= end) ?? []

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
    return { line, bands }
  }
  const anomaly850 = anomaly(t850.values, climate850)
  const { climate2mHeight } = temperatures
  const show2m = climate2mHeight !== undefined
    && Math.abs(climate2mHeight - t2mEcmwf.height) <= MAX_CLIMATE_HEIGHT_DIFFERENCE
  // Without a comparable ERA5 point the T2m panel shows no climate at all: line and bars would mislead.
  // Daily means, not terms: against a climate per term the daily cycle would dominate the anomaly.
  const shownClimate2m = show2m ? climate2m : []
  const anomaly2m = dailyAnomaly(t2mEcmwf.values, shownClimate2m)
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
  const thetaELines: ScaledLine[] = thetae850 === null
    ? []
    : [{ values: thetae850.values, className: styles.thetaE, range: THETA_E_RANGE }]

  const humidityLegend: LegendEntry[] = td2m !== null && tw2m !== null
    ? [{ lines: [styles.dewPoint, styles.wetBulb], text: 'ECMWF Taupunkt (blau), Feuchtkugeltemperatur (grün)' }]
    : [
        ...(td2m === null ? [] : [{ line: styles.dewPoint, text: 'ECMWF Taupunkt' }]),
        ...(tw2m === null ? [] : [{ line: styles.wetBulb, text: 'ECMWF Feuchtkugeltemperatur' }]),
      ]

  const panels: PanelSpec[] = [
    {
      key: 't2m',
      title: ['Temperatur in 2 m (°C)',
        ...(td2m === null ? [] : ['Taupunkt']),
        ...(tw2m === null ? [] : ['Feuchtkugel']),
        ...(gust10m === null ? [] : ['Böen in 10 m'])].join(', '),
      legend: [
        { line: styles.t2mEcmwf, text: `ECMWF ${pointLabel(t2mEcmwf.point, t2mEcmwf.height)}` },
        ...(t2mRegional === null ? [] : [{ line: styles.t2mRegional, text: `${t2mRegional.model} ${pointLabel(t2mRegional.point, t2mRegional.height)}` }]),
        // Same grid point as the ECMWF T2m; one row for both, so the plot keeps its height on a phone.
        ...humidityLegend,
      ],
      // Climate mean first, then dew point and wet-bulb temperature, so the T2m lines lie on top of them; the bars
      // lie below all lines.
      lines: [
        { values: anomaly2m.line, className: styles.climate },
        ...(td2m === null ? [] : [{ values: td2m.values, className: styles.dewPoint }]),
        ...(tw2m === null ? [] : [{ values: tw2m.values, className: styles.wetBulb }]),
        { values: t2mEcmwf.values, className: styles.t2mEcmwf },
        ...(regional.length > 0 ? [{ values: regional, className: styles.t2mRegional }] : []),
      ],
      bands: anomaly2m.bands,
      // The bands of the wind10m chart, so a colour means the same speed in the diagram and on the map; no legend or
      // tooltip value (per user: the exact speed does not matter).
      ...(gust10m === null ? {} : { colourBar: { values: gust10m.series.values, colours: gust10m.colours } }),
      axis: TEMPERATURE_SCALE,
      weight: 1,
    },
    {
      key: 't850',
      title: ['Temperatur in 850 hPa (°C)', ...(thetae850 === null ? [] : ['θe']),
        ...(precip6h === null ? [] : ['Niederschlag 3/6 h']),
        ...(precip6h === null || tcc === null ? [] : ['Bewölkung'])].join(', '),
      legend: [
        { line: styles.t850, text: `ECMWF ${pointLabel(t850.point, t850.height)}` },
        ...(thetae850 === null ? [] : [{ line: styles.thetaE, text: 'ECMWF θe 850 hPa, Achse unten mit 0 %, oben mit 100 % RH' }]),
      ],
      lines: [
        { values: anomaly850.line, className: styles.climate },
        { values: t850.values, className: styles.t850 },
      ],
      bands: anomaly850.bands,
      scaledLines: thetaELines,
      // The bands, the interval and the type symbols of the weather_summary chart, so a colour means the same
      // amount in the diagram and on the map; like the gusts no legend or tooltip value. Dry blocks show the cloud
      // cover at their step in the greys of the chart, which also draws the precipitation over the clouds.
      ...(precip6h === null ? {} : {
        colourBar: {
          values: precip6h.series.values, colours: precip6h.colours, transparentBelow: precip6h.transparentBelow,
          ...(tcc === null ? {} : {
            fallback: { values: tcc.series.values, colours: tcc.colours, transparentBelow: tcc.transparentBelow },
          }),
          marks: precip6h.types.flatMap((p) => {
            const mark = PRECIP_TYPE_MARKS[p.value]
            return mark === undefined ? [] : [{ valid: p.valid, ...mark }]
          }),
        },
      }),
      axis: TEMPERATURE_SCALE,
      weight: 1,
    },
    ...(thickness === null ? [] : [{
      key: 'thickness',
      title: ['Schichtdicke 1000–500 hPa (dam)', ...(hasTotals ? ['Showalter-Index'] : []), ...(rh700 === null ? [] : ['RH 700 hPa'])].join(', '),
      legend: [
        { line: styles.thickness, text: `ECMWF ${pointLabel(thickness.point, thickness.height)}` },
        ...(rh700 === null ? [] : [{ line: styles.rh700, text: 'ECMWF RH 700 hPa, Achse unten 0 %, oben 100 %' }]),
      ],
      lines: [{ values: thickness.values, className: styles.thickness }],
      ...(rh700 === null ? {} : { scaledLines: [{ values: rh700.values, className: styles.rh700, range: PERCENT_RANGE }] }),
      ...(!hasTotals ? {} : {
        centred: { polygons: showalterBands, extent, maxScale: THICKNESS_PER_KELVIN, classes: showalterClasses },
      }),
      axis: THICKNESS_SCALE,
      weight: 1,
    }]),
  ]

  const placed = placePanels(panels, MARGIN_TOP, size.height, PANEL_GAP)

  /** Value per valid time of a series, for the tooltips. */
  const byTime = (values: ValuePoint[] | undefined) => new Map(values?.map((p) => [+p.valid, p.value]) ?? [])
  const t2mEcmwfByTime = byTime(t2mEcmwf.values)
  const t2mRegionalByTime = byTime(regional)
  const wetBulbByTime = byTime(tw2m?.values)
  const dewPointByTime = byTime(td2m?.values)
  const t850ByTime = byTime(t850.values)
  const thetaEByTime = byTime(thetae850?.values)
  const thicknessByTime = byTime(thickness?.values)
  const rh700ByTime = byTime(rh700?.values)
  /** "T850 5,3 °C" of a series at a valid time; null where it has no value. */
  const part = (series: Map<number, number>, time: number, label: string, unit: string, digits = 1) => {
    const value = series.get(time)
    return value === undefined ? null : `${label} ${decimals(value, digits)} ${unit}`
  }
  // Each panel's tooltip holds only its own series, so it stays short.
  const tooltipParts: Record<string, (time: number) => (string | null)[]> = {
    t2m: (t) => [part(t2mEcmwfByTime, t, 'T2m ECMWF', '°C'), part(t2mRegionalByTime, t, `T2m ${t2mRegional?.model}`, '°C'),
      part(wetBulbByTime, t, 'Feuchtkugel', '°C'), part(dewPointByTime, t, 'Taupunkt', '°C')],
    t850: (t) => [part(t850ByTime, t, 'T850', '°C'), part(thetaEByTime, t, 'θe', 'K')],
    thickness: (t) => [part(thicknessByTime, t, 'Z1000–500', 'dam'), part(rh700ByTime, t, 'RH700', '%', 0)],
  }
  const tooltip = (key: string, valid: Date) =>
    [timeLabel(valid), ...tooltipParts[key](+valid).filter((p) => p !== null)].join(' · ')
  const columns = t850.values.map((p) => x(p.valid))
  const save = () => {
    if (svg.current === null || box.current === null) return
    // The surface colour of the cell, so the file looks like the diagram on the page.
    const background = getComputedStyle(box.current).getPropertyValue('--surface').trim() || '#fff'
    downloadSvg(svg.current, exportFileName(t850.point, t850.values[0].valid), background)
  }

  return (
    <div ref={box} className={styles.diagram}>
      {size.width > 0 && size.height > 0 && (
        <svg ref={svg} className={styles.svg} viewBox={`0 0 ${size.width} ${size.height}`} role="img"
          aria-label="T2m von ECMWF und einem Regionalmodell (ICON-D2 oder ALADIN), Taupunkt und Feuchtkugeltemperatur in 2 m von ECMWF, Abweichung des Tagesmittels vom Klimamittel und Böen in 10 m von ECMWF, T850 von ECMWF mit Abweichung vom Klimamittel und äquivalentpotentieller Temperatur in 850 hPa und Niederschlag über 6 Stunden mit Schnee und gefrierendem Niederschlag sowie Bewölkung von ECMWF, Schichtdicke 1000–500 hPa, Showalter-Index eines Pakets aus 850 hPa mit Taupunkt, relative Feuchte in 700 hPa">
          {placed.map((p) => <TemperaturePanel key={p.panel.key} placed={p} time={time} left={PLOT_LEFT} right={plotRight} />)}
          {t850.values.map((point, i) => {
            // Each hover column reaches halfway to its neighbours, so the 3 h and 6 h steps cover the plots without gaps.
            const left = i === 0 ? PLOT_LEFT : (columns[i - 1] + columns[i]) / 2
            const right = i === columns.length - 1 ? plotRight : (columns[i] + columns[i + 1]) / 2
            return (
              // The cross shows in every panel, the tooltip is the one of the panel under the mouse.
              <g key={+point.valid} className={styles.hit} {...{ [EXPORT_SKIP]: '' }}>
                {placed.map(({ panel, plotTop, plotBottom }) => (
                  <g key={panel.key}>
                    <title>{tooltip(panel.key, point.valid)}</title>
                    <rect x={left} y={plotTop} width={right - left} height={plotBottom - plotTop} />
                    <line className={styles.cross} x1={columns[i]} x2={columns[i]} y1={plotTop} y2={plotBottom} />
                  </g>
                ))}
              </g>
            )
          })}
        </svg>
      )}
      {size.width > 0 && size.height > 0 && (
        <button type="button" className={styles.download} onClick={save} title="Diagramm als SVG herunterladen">
          SVG ↓
        </button>
      )}
    </div>
  )
}
