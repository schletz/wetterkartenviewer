import { WARM } from '../model/anomalyBands'
import { holidayName } from '../model/holidays'
import { LEGEND_LINE_HEIGHT, TITLE_HEIGHT, type PlacedPanel, type TimeAxis } from '../model/panelLayout'
import type { ValuePoint } from '../model/TemperatureSeries'
import { ValueAxis } from '../model/ValueAxis'
import styles from './TemperatureDiagram.module.css'

const LEGEND_SWATCH_WIDTH = 22
const MIN_DAY_LABEL_WIDTH = 26
const DAY_MS = 86_400_000
const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
/** Share of the half plot height the largest centred area may fill. */
const CENTRED_FILL = 0.9

interface TemperaturePanelProps {
  placed: PlacedPanel
  time: TimeAxis
  left: number
  right: number
}

/** "Mo 2" of a UTC day, as in the ENS meteograms. */
function dayLabel(day: Date): string {
  return `${WEEKDAYS[day.getUTCDay()]} ${day.getUTCDate()}`
}

/**
 * One panel of the temperature diagram as SVG group, laid out like a panel of the ENS meteograms:
 * title and legend, the plot with its own value axis, below it the day labels.
 */
export default function TemperaturePanel({ placed, time, left, right }: TemperaturePanelProps) {
  const { panel, top, plotTop, plotBottom } = placed
  const { x } = time
  const values = panel.lines.flatMap((line) => line.values.flatMap((p) => (p === null ? [] : [p.value])))
  const axis = new ValueAxis(values, plotTop, plotBottom, panel.steps)
  const clipId = `temperature-${panel.key}`
  // Centred areas: zero in the middle of the axis, shrunk below maxScale only if the largest would leave the plot.
  const centre = (axis.min + axis.max) / 2
  const centred = panel.centred
  const centredScale = centred === undefined || centred.extent <= 0
    ? 0
    : Math.min(centred.maxScale, (CENTRED_FILL * (axis.max - centre)) / centred.extent)

  const path = (points: (ValuePoint | null)[]) => {
    let penDown = false
    return points.map((point) => {
      if (point === null) {
        penDown = false
        return ''
      }
      const command = `${penDown ? 'L' : 'M'}${x(point.valid).toFixed(1)},${axis.y(point.value).toFixed(1)}`
      penDown = true
      return command
    }).join(' ')
  }

  return (
    <g>
      <defs>
        <clipPath id={clipId}>
          <rect x={left} y={plotTop} width={right - left} height={plotBottom - plotTop} />
        </clipPath>
      </defs>
      <text className={styles.panelTitle} x={left} y={top + 12}>{panel.title}</text>
      {panel.legend.map((entry, i) => {
        const y = top + TITLE_HEIGHT + i * LEGEND_LINE_HEIGHT + 7
        return (
          <g key={entry.text}>
            {'line' in entry
              ? <line className={`${styles.line} ${entry.line}`} x1={left} x2={left + LEGEND_SWATCH_WIDTH - 4} y1={y} y2={y} />
              : 'bands' in entry ? <BandSwatch x={left} y={y} /> : <SignSwatch x={left} y={y} />}
            <text x={left + LEGEND_SWATCH_WIDTH} y={y + 4}>{entry.text}</text>
          </g>
        )
      })}
      {axis.ticks().map((value) => (
        <g key={value}>
          <line className={value === 0 ? styles.zero : styles.grid} x1={left} x2={right} y1={axis.y(value)} y2={axis.y(value)} />
          <text x={left - 6} y={axis.y(value) + 4} textAnchor="end">{value}</text>
        </g>
      ))}
      {time.days.map((day) => {
        const date = new Date(day)
        const from = x(Math.max(day, time.start))
        const to = x(Math.min(day + DAY_MS, time.end))
        const red = date.getUTCDay() === 0 || holidayName(date) !== undefined
        return (
          <g key={day}>
            {day >= time.start && <line className={styles.grid} x1={x(day)} x2={x(day)} y1={plotTop} y2={plotBottom} />}
            {to - from >= MIN_DAY_LABEL_WIDTH && (
              <text className={red ? styles.holiday : undefined} x={(from + to) / 2} y={plotBottom + 20}
                textAnchor="middle">{dayLabel(date)}<title>{holidayName(date)}</title></text>
            )}
          </g>
        )
      })}
      {time.ticks.map((tick) => (
        <line key={tick} className={styles.axis} x1={x(tick)} x2={x(tick)} y1={plotBottom}
          y2={plotBottom + (new Date(tick).getUTCHours() === 0 ? 7 : 4)} />
      ))}
      <rect className={styles.frame} x={left} y={plotTop} width={right - left} height={plotBottom - plotTop} />
      <g clipPath={`url(#${clipId})`}>
        {panel.bands?.map((band, i) => (
          <polygon key={i} className={band.side === WARM ? styles.warm : styles.cold}
            points={band.vertices.map(([vx, value]) => `${vx.toFixed(1)},${axis.y(value).toFixed(1)}`).join(' ')} />
        ))}
        {centred?.polygons.map((band, i) => (
          <polygon key={`centred-${i}`} className={`${band.side === WARM ? styles.warm : styles.cold} ${styles.signed}`}
            points={band.vertices.map(([vx, value]) => `${vx.toFixed(1)},${axis.y(centre + value * centredScale).toFixed(1)}`).join(' ')} />
        ))}
        {centred !== undefined && (
          <line className={`${styles.line} ${styles.parcel}`} x1={left} x2={right} y1={axis.y(centre)} y2={axis.y(centre)} />
        )}
        {panel.lines.map((line) => <path key={line.className} className={`${styles.line} ${line.className}`} d={path(line.values)} />)}
      </g>
    </g>
  )
}

/** Legend swatch of the centred areas: warm above, cold below, the zero line between. */
function SignSwatch({ x, y }: { x: number; y: number }) {
  const width = LEGEND_SWATCH_WIDTH - 4
  return (
    <g>
      <rect className={`${styles.warm} ${styles.signed}`} x={x} y={y - 6} width={width} height={6} />
      <rect className={`${styles.cold} ${styles.signed}`} x={x} y={y} width={width} height={6} />
      <line className={`${styles.line} ${styles.parcel}`} x1={x} x2={x + width} y1={y} y2={y} />
    </g>
  )
}

/** Legend swatch of the anomaly areas: warm above, cold below, every σ layer darker to the right, the climate mean between. */
function BandSwatch({ x, y }: { x: number; y: number }) {
  const width = (LEGEND_SWATCH_WIDTH - 4) / 3
  return (
    <g>
      {[0, 1, 2].map((k) => (
        // Layer k covers column k and all to the right of it, so the shade adds up to the right.
        <g key={k}>
          <rect className={styles.warm} x={x + k * width} y={y - 6} width={(3 - k) * width} height={6} />
          <rect className={styles.cold} x={x + k * width} y={y} width={(3 - k) * width} height={6} />
        </g>
      ))}
      <line className={`${styles.line} ${styles.climate}`} x1={x} x2={x + LEGEND_SWATCH_WIDTH - 4} y1={y} y2={y} />
    </g>
  )
}
