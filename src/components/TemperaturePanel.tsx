import { WARM } from '../model/anomalyBands'
import { bandColour } from '../model/colourBands'
import { holidayName } from '../model/holidays'
import {
  COLOUR_BAR_HEIGHT, LEGEND_LINE_HEIGHT, TITLE_HEIGHT,
  type ColourBar, type PlacedPanel, type ScaledLine, type TimeAxis,
} from '../model/panelLayout'
import type { ValuePoint } from '../model/TemperatureSeries'
import { ValueAxis } from '../model/ValueAxis'
import styles from './TemperatureDiagram.module.css'

const LEGEND_SWATCH_WIDTH = 22
/** Vertical distance of the line swatches stacked in one legend row. */
const STACKED_SWATCH_GAP = 4
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
  // A colour bar takes the bottom rows of the plot, so no line runs across it.
  const axisBottom = panel.colourBar === undefined ? plotBottom : plotBottom - COLOUR_BAR_HEIGHT
  const axis = new ValueAxis(values, plotTop, axisBottom, panel.steps)
  const clipId = `temperature-${panel.key}`
  // Centred areas: zero in the middle of the axis, shrunk below maxScale only if the largest would leave the plot.
  const centre = (axis.min + axis.max) / 2
  const centred = panel.centred
  const centredScale = centred === undefined || centred.extent <= 0
    ? 0
    : Math.min(centred.maxScale, (CENTRED_FILL * (axis.max - centre)) / centred.extent)

  // A scaled line maps its range linearly onto the axis range, clamped to it.
  const scaledY = (line: ScaledLine) => {
    const [low, high] = line.range(axis.min, axis.max)
    return (value: number) => {
      const share = Math.min(1, Math.max(0, (value - low) / (high - low)))
      return axis.y(axis.min + share * (axis.max - axis.min))
    }
  }

  const path = (points: (ValuePoint | null)[], y: (value: number) => number = (value) => axis.y(value)) => {
    let penDown = false
    return points.map((point) => {
      if (point === null) {
        penDown = false
        return ''
      }
      const command = `${penDown ? 'L' : 'M'}${x(point.valid).toFixed(1)},${y(point.value).toFixed(1)}`
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
            {'line' in entry && <line className={`${styles.line} ${entry.line}`} x1={left} x2={left + LEGEND_SWATCH_WIDTH - 4} y1={y} y2={y} />}
            {'lines' in entry && entry.lines.map((line, k) => {
              // Centred on the row: the first on top.
              const offset = (k - (entry.lines.length - 1) / 2) * STACKED_SWATCH_GAP
              return <line key={line} className={`${styles.line} ${line}`} x1={left} x2={left + LEGEND_SWATCH_WIDTH - 4} y1={y + offset} y2={y + offset} />
            })}
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
      {panel.colourBar !== undefined && (
        <ColourStrip bar={panel.colourBar} x={x} left={left} right={right} top={axisBottom} bottom={plotBottom} />
      )}
      <rect className={styles.frame} x={left} y={plotTop} width={right - left} height={plotBottom - plotTop} />
      <g clipPath={`url(#${clipId})`}>
        {panel.bands?.map((band, i) => (
          <polygon key={i} className={band.side === WARM ? styles.warm : styles.cold}
            points={band.vertices.map(([vx, value]) => `${vx.toFixed(1)},${axis.y(value).toFixed(1)}`).join(' ')} />
        ))}
        {centred?.polygons.map((band, i) => (
          <polygon key={`centred-${i}`} className={band.side === WARM ? centred.classes.above : centred.classes.below}
            points={band.vertices.map(([vx, value]) => `${vx.toFixed(1)},${axis.y(centre + value * centredScale).toFixed(1)}`).join(' ')} />
        ))}
        {centred !== undefined && (
          <line className={`${styles.line} ${centred.classes.line}`} x1={left} x2={right} y1={axis.y(centre)} y2={axis.y(centre)} />
        )}
        {panel.scaledLines?.map((line) => (
          <path key={line.className} className={`${styles.line} ${line.className}`} d={path(line.values, scaledY(line))} />
        ))}
        {panel.lines.map((line) => <path key={line.className} className={`${styles.line} ${line.className}`} d={path(line.values)} />)}
      </g>
    </g>
  )
}

/** The colour bar between `top` and `bottom`: each value fills the time halfway to its neighbours. */
function ColourStrip({ bar, x, left, right, top, bottom }: {
  bar: ColourBar; x: TimeAxis['x']; left: number; right: number; top: number; bottom: number
}) {
  const columns = bar.values.map((p) => Math.min(right, Math.max(left, x(p.valid))))
  return (
    <g>
      {bar.values.map((point, i) => {
        const from = i === 0 ? left : (columns[i - 1] + columns[i]) / 2
        const to = i === columns.length - 1 ? right : (columns[i] + columns[i + 1]) / 2
        // Steps outside the time axis collapse to zero width at its ends.
        return to > from && (
          <rect key={+point.valid} x={from} y={top} width={to - from} height={bottom - top}
            fill={bandColour(bar.colours, point.value)} />
        )
      })}
      <line className={styles.axis} x1={left} x2={right} y1={top} y2={top} />
    </g>
  )
}
