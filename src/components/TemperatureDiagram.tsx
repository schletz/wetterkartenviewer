import { useRef } from 'react'
import { useElementSize } from '../hooks/useElementSize'
import { anomalyPolygons } from '../model/anomalyBands'
import { parcelLift } from '../model/moistAdiabat'
import type { GeoLocation } from '../model/GeoLocation'
import { placePanels, type PanelSpec, type TimeAxis } from '../model/panelLayout'
import type { LocationTemperatures, ValuePoint } from '../model/TemperatureSeries'
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
const TICK_HOURS = 6
const HOUR_MS = 3_600_000
const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
/**
 * Vertical totals share the thickness axis: TOTALS_MEAN K lies at THICKNESS_MEAN dam, 1 K spans
 * THICKNESS_PER_KELVIN dam. Only their position against the parcel reference counts, so they need no axis of
 * their own. The means are those of Austria: ERA5 1991–2020 monthly T850 over its 163 grid points averages
 * 5.0 °C, i.e. 552 dam with the coupling 544 dam + 1.6 dam/K × T850 of the synop skill, and the totals of a
 * saturated parcel at the monthly means average 27.2 K. With the skill's 1.6 dam/K, 1 K of vertical totals is as tall as
 * 1 K of T850, and their swings stay as large as those of the thickness.
 */
const THICKNESS_MEAN = 552
const TOTALS_MEAN = 27
const THICKNESS_PER_KELVIN = 1.6

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

/** "Mo 2.11. 06 UTC" */
function timeLabel(time: Date): string {
  return `${WEEKDAYS[time.getUTCDay()]} ${time.getUTCDate()}.${time.getUTCMonth() + 1}. ${String(time.getUTCHours()).padStart(2, '0')} UTC`
}

/**
 * Meteogram of T2m (ECMWF and ICON-D2), T850 (ECMWF) with its anomaly against the ERA5 climate, the
 * ECMWF 1000–500 hPa thickness with the vertical totals T850 − T500 on its axis, against those of a parcel
 * lifted from 850 hPa with its dew point from RH850 (above them the Showalter index is negative), in panels one
 * below the other like the ENS meteograms. Fills its parent.
 */
export default function TemperatureDiagram({ temperatures }: TemperatureDiagramProps) {
  const box = useRef<HTMLDivElement>(null)
  const size = useElementSize(box)
  const { t850, climate850, t2mEcmwf, t2mIcon, thickness, t500, rh850 } = temperatures

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

  const climateLine = t850.values.map((p, i) => {
    const climate = climate850[i]
    return climate === null ? null : { valid: p.valid, value: climate.mean }
  })
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
  const totals = pairs.map((q) => q && { valid: q.valid, value: q.totals })
  const parcelTotals = pairs.map((q) => q && { valid: q.valid, value: q.parcel.totals })
  const onThicknessAxis = (point: ValuePoint | null) => point === null
    ? null
    : { valid: point.valid, value: THICKNESS_MEAN + THICKNESS_PER_KELVIN * (point.value - TOTALS_MEAN) }

  const bands = anomalyPolygons(t850.values.map((p, i) => {
    const climate = climate850[i]
    return climate === null ? null : { x: x(p.valid), value: p.value, mean: climate.mean, std: climate.std }
  }), SIGMA_STEPS)

  const panels: PanelSpec[] = [
    {
      key: 't2m',
      title: 'Temperatur in 2 m (°C)',
      legend: [
        { line: styles.t2mEcmwf, text: `ECMWF ${pointLabel(t2mEcmwf.point, t2mEcmwf.height)}` },
        ...(t2mIcon === null ? [] : [{ line: styles.t2mIcon, text: `ICON-D2 ${pointLabel(t2mIcon.point, t2mIcon.height)}` }]),
      ],
      lines: [
        { values: t2mEcmwf.values, className: styles.t2mEcmwf },
        ...(icon.length > 0 ? [{ values: icon, className: styles.t2mIcon }] : []),
      ],
      steps: TEMPERATURE_STEPS,
      weight: 1,
    },
    {
      key: 't850',
      title: 'Temperatur in 850 hPa (°C)',
      legend: [
        { line: styles.t850, text: `ECMWF ${pointLabel(t850.point, t850.height)}` },
        { bands: true, text: `Ø ${temperatures.period} ERA5 ${pointLabel(temperatures.climatePoint)}, ±${SIGMA_STEPS.slice(1).join('/')} σ` },
      ],
      lines: [
        { values: climateLine, className: styles.climate },
        { values: t850.values, className: styles.t850 },
      ],
      bands,
      steps: TEMPERATURE_STEPS,
      weight: 1,
    },
    ...(thickness === null ? [] : [{
      key: 'thickness',
      title: !hasTotals ? 'Schichtdicke 1000–500 hPa (dam)' : 'Schichtdicke 1000–500 hPa (dam), Vertical Totals',
      legend: [
        { line: styles.thickness, text: `ECMWF ${pointLabel(thickness.point, thickness.height)}` },
        ...(!hasTotals ? [] : [
          { line: styles.totals, text: `T850 − T500, 1 K ≙ ${decimals(THICKNESS_PER_KELVIN, 1)} dam` },
          { line: styles.moistAdiabat, text: 'T850 − T500 Paket aus 850 hPa mit Taupunkt, darüber labil (Showalter < 0)' },
        ]),
      ],
      lines: [
        ...(!hasTotals ? [] : [
          { values: parcelTotals.map(onThicknessAxis), className: styles.moistAdiabat },
          { values: totals.map(onThicknessAxis), className: styles.totals },
        ]),
        { values: thickness.values, className: styles.thickness },
      ],
      steps: THICKNESS_STEPS,
      weight: 1,
    }]),
  ]

  const placed = placePanels(panels, MARGIN_TOP, size.height, PANEL_GAP)

  const iconByTime = new Map(icon.map((p) => [+p.valid, p.value]))
  const ecmwfByTime = new Map(t2mEcmwf.values.map((p) => [+p.valid, p.value]))
  const thicknessByTime = new Map(thickness?.values.map((p) => [+p.valid, p.value]) ?? [])
  const columns = t850.values.map((p) => x(p.valid))
  const tooltip = (point: ValuePoint, i: number) => {
    const parts = [timeLabel(point.valid)]
    const ecmwf = ecmwfByTime.get(+point.valid)
    if (ecmwf !== undefined) parts.push(`T2m ECMWF ${decimals(ecmwf, 1)} °C`)
    const iconValue = iconByTime.get(+point.valid)
    if (iconValue !== undefined) parts.push(`T2m ICON-D2 ${decimals(iconValue, 1)} °C`)
    parts.push(`T850 ${decimals(point.value, 1)} °C`)
    const climate = climate850[i]
    if (climate !== null) {
      parts.push(`Ø ${decimals(climate.mean, 1)} °C`)
      if (climate.std > 0) {
        const sigma = (point.value - climate.mean) / climate.std
        parts.push(`${sigma >= 0 ? '+' : ''}${decimals(sigma, 1)} σ`)
      }
    }
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
    if (pair !== null) {
      const showalter = pair.parcel.totals - pair.totals
      parts.push(`Showalter ${showalter >= 0 ? '+' : ''}${decimals(showalter, 1)} K`)
    }
    return parts.join(' · ')
  }

  return (
    <div ref={box} className={styles.diagram}>
      {size.width > 0 && size.height > 0 && (
        <svg className={styles.svg} viewBox={`0 0 ${size.width} ${size.height}`} role="img"
          aria-label="T2m von ECMWF und ICON-D2, T850 von ECMWF mit Abweichung vom Klimamittel, Schichtdicke 1000–500 hPa, Vertical Totals gegen ein Paket aus 850 hPa mit Taupunkt">
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
