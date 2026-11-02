import { useRef } from 'react'
import { useElementSize } from '../hooks/useElementSize'
import { anomalyPolygons } from '../model/anomalyBands'
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
 * Meteogram of T2m (ECMWF and ICON-D2), T850 (ECMWF) with its anomaly against the ERA5 climate and the
 * ECMWF 1000–500 hPa thickness, in panels one below the other like the ENS meteograms. Fills its parent.
 */
export default function TemperatureDiagram({ temperatures }: TemperatureDiagramProps) {
  const box = useRef<HTMLDivElement>(null)
  const size = useElementSize(box)
  const { t850, climate850, t2mEcmwf, t2mIcon, thickness } = temperatures

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
      title: 'Schichtdicke 1000–500 hPa (dam)',
      legend: [{ line: styles.thickness, text: `ECMWF ${pointLabel(thickness.point, thickness.height)}` }],
      lines: [{ values: thickness.values, className: styles.thickness }],
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
    return parts.join(' · ')
  }

  return (
    <div ref={box} className={styles.diagram}>
      {size.width > 0 && size.height > 0 && (
        <svg className={styles.svg} viewBox={`0 0 ${size.width} ${size.height}`} role="img"
          aria-label="T2m von ECMWF und ICON-D2, T850 von ECMWF mit Abweichung vom Klimamittel, Schichtdicke 1000–500 hPa">
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
