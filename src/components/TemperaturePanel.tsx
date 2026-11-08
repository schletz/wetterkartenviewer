import { WARM } from '../model/anomalyBands'
import { bandColour } from '../model/colourBands'
import { holidayName } from '../model/holidays'
import {
  COLOUR_BAR_HEIGHT, LEGEND_LINE_HEIGHT, TITLE_HEIGHT,
  type BarMark, type ColourBar, type ColourLayer, type PlacedPanel, type ScaledLine, type TimeAxis,
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
/** Radius of a symbol over a colour bar, px: a 3 h block is about 6 px wide on a desktop. */
const MARK_RADIUS = 3.5
/** Gap between a symbol and the top of the colour bar, px. */
const MARK_GAP = 2
const COS_30 = Math.cos(Math.PI / 6)

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
  const axis = new ValueAxis(values, plotTop, axisBottom, panel.axis)
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
          {axis.labelled(value) && <text x={left - 6} y={axis.y(value) + 4} textAnchor="end">{value}</text>}
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
      {/* On top of the lines, which seldom reach the bottom of the axis. */}
      {panel.colourBar?.marks !== undefined && (
        <BarMarks bar={panel.colourBar} x={x} left={left} right={right} y={axisBottom - MARK_GAP - MARK_RADIUS} />
      )}
    </g>
  )
}

/** Colour of a value in a layer; undefined below `transparentBelow`. */
function layerColour(layer: ColourLayer, value: number): string | undefined {
  return layer.transparentBelow !== undefined && value < layer.transparentBelow
    ? undefined
    : bandColour(layer.colours, value)
}

/**
 * The colour bar between `top` and `bottom`: each value ends at its valid time and fills the time back to the previous
 * value. A value below `transparentBelow` leaves it to the fallback layer, or empty.
 */
function ColourStrip({ bar, x, left, right, top, bottom }: {
  bar: ColourBar; x: TimeAxis['x']; left: number; right: number; top: number; bottom: number
}) {
  const blocks = barBlocks(bar, x, left, right)
  const { fallback } = bar
  const fallbackByTime = new Map(fallback?.values.map((p) => [+p.valid, p.value]))
  const blockColour = (point: ValuePoint) => {
    const other = fallbackByTime.get(+point.valid)
    return layerColour(bar, point.value)
      ?? (fallback === undefined || other === undefined ? undefined : layerColour(fallback, other))
  }
  return (
    <g>
      {bar.values.map((point, i) => {
        const [from, to] = blocks[i]
        const fill = blockColour(point)
        // Steps outside the time axis collapse to zero width at its ends.
        return to > from && fill !== undefined && (
          <rect key={+point.valid} x={from} y={top} width={to - from} height={bottom - top} fill={fill} />
        )
      })}
      <line className={styles.axis} x1={left} x2={right} y1={top} y2={top} />
    </g>
  )
}

/**
 * Horizontal extent of every block of a colour bar. The values cover the interval before their step (gust maximum,
 * precipitation sum), so a block ends at its step and reaches back to the previous one; the first reaches back to the
 * start of the axis, the run (T+0), where its interval begins.
 */
function barBlocks(bar: ColourBar, x: TimeAxis['x'], left: number, right: number): [from: number, to: number][] {
  const columns = bar.values.map((p) => Math.min(right, Math.max(left, x(p.valid))))
  return columns.map((to, i) => [i === 0 ? left : columns[i - 1], to])
}

/** The symbols of a colour bar, centred over their blocks at height `y`. */
function BarMarks({ bar, x, left, right, y }: {
  bar: ColourBar; x: TimeAxis['x']; left: number; right: number; y: number
}) {
  const blocks = barBlocks(bar, x, left, right)
  const index = new Map(bar.values.map((p, i) => [+p.valid, i]))
  return (
    <g>
      {bar.marks?.map((mark) => {
        const i = index.get(+mark.valid)
        if (i === undefined || blocks[i][1] <= blocks[i][0]) return null
        const cx = (blocks[i][0] + blocks[i][1]) / 2
        const shape = markShape(mark, cx, y)
        return (
          <g key={+mark.valid}>
            {mark.haloClassName !== undefined && shape(mark.haloClassName)}
            {shape(mark.className)}
          </g>
        )
      })}
    </g>
  )
}

/** Draws the shape of a mark centred at (cx, cy) with a class: an asterisk of three spokes, one upright, or a diamond. */
function markShape(mark: BarMark, cx: number, cy: number) {
  const r = MARK_RADIUS
  if (mark.shape === 'diamond') {
    const points = `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`
    return (className: string) => <polygon className={className} points={points} />
  }
  const dx = r * COS_30
  const dy = r / 2
  const d = `M${cx},${cy - r}L${cx},${cy + r}M${cx - dx},${cy - dy}L${cx + dx},${cy + dy}M${cx - dx},${cy + dy}L${cx + dx},${cy - dy}`
  return (className: string) => <path className={className} d={d} />
}
