import { useRef } from 'react'
import { useElementSize } from '../hooks/useElementSize'
import { measuredRuns, type MeasuredSample, type StationSeries } from '../model/stationSeries'
import { STATION_TEMPERATURE_SCALE, ValueAxis } from '../model/ValueAxis'
import styles from './StationChart.module.css'

interface StationChartProps {
  stationName: string
  series: StationSeries
}

/** Pixels around the plot: the right margin holds the label of the „aktuell“ line. */
const MARGIN = { left: 56, right: 28, top: 54, bottom: 28 }
const HOUR_MS = 60 * 60 * 1000
const SLOT_MS = 10 * 60 * 1000
const TICK_HOURS = 6
/** Half the width of a day label, which must stay inside the diagram at the right edge. */
const DAY_LABEL_HALF_WIDTH = 34
/** Pixels per day below which the day labels drop the year, so they do not run into each other. */
const FULL_DATE_DAY_WIDTH = 80
/** Diagram width below which the title leaves out the station name, which the title bar of the window shows anyway. */
const NAMED_TITLE_WIDTH = 420

const VALUE_FORMAT = new Intl.NumberFormat('de-AT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

/** „05.11.“ or „05.11.2026“, the UTC day of a day line. */
function dayLabel(time: Date, withYear: boolean): string {
  return `${pad(time.getUTCDate())}.${pad(time.getUTCMonth() + 1)}.${withYear ? time.getUTCFullYear() : ''}`
}

/** „08:33“ in UTC. */
function utcClock(time: Date): string {
  return `${pad(time.getUTCHours())}:${pad(time.getUTCMinutes())}`
}

/** Tooltip of a measurement, e.g. „So 08.11. 07:40 UTC · 2,4 °C“. */
function tooltip({ time, value }: MeasuredSample): string {
  const day = `${WEEKDAYS[time.getUTCDay()]} ${pad(time.getUTCDate())}.${pad(time.getUTCMonth() + 1)}.`
  return `${day} ${utcClock(time)} UTC · ${VALUE_FORMAT.format(value)} °C`
}

/**
 * Line and area diagram of the 10 min air temperature, time axis in UTC. The time axis runs from `series.start`
 * to the moment of the request, marked by the „aktuell“ line; the value axis has a 2 K grid and spans at least 20 K.
 * Drawn in the pixels of its box, like the temperature diagram, so text keeps its size at any window size.
 */
export default function StationChart({ stationName, series }: StationChartProps) {
  const box = useRef<HTMLDivElement>(null)
  const { width, height } = useElementSize(box)
  const runs = measuredRuns(series.samples)
  const measured = runs.flat()

  const right = width - MARGIN.right
  const bottom = height - MARGIN.bottom
  const startMs = series.start.getTime()
  const endMs = series.end.getTime()
  const x = (ms: number) => MARGIN.left + ((ms - startMs) / (endMs - startMs)) * (right - MARGIN.left)

  const render = () => {
    const axis = new ValueAxis(measured.map((sample) => sample.value), MARGIN.top, bottom, STATION_TEMPERATURE_SCALE)
    // The area reaches to the zero line, or to the edge of the plot if the axis does not contain 0.
    const baseline = axis.y(Math.min(axis.max, Math.max(axis.min, 0)))
    const points = (run: MeasuredSample[]) => run
      .map(({ time, value }) => `${x(time.getTime()).toFixed(1)},${axis.y(value).toFixed(1)}`)
      .join(' L')
    const edge = (sample: MeasuredSample) => x(sample.time.getTime()).toFixed(1)
    const columnWidth = x(startMs + SLOT_MS) - x(startMs)

    const ticks: number[] = []
    for (let ms = startMs; ms <= endMs; ms += TICK_HOURS * HOUR_MS) ticks.push(ms)
    const isDay = (ms: number) => (ms - startMs) % (24 * HOUR_MS) === 0
    const withYear = x(startMs + 24 * HOUR_MS) - x(startMs) >= FULL_DATE_DAY_WIDTH

    return (
      <>
        {axis.ticks().map((value) => (
          <g key={value}>
            <line className={value === 0 ? styles.zero : styles.grid}
              x1={MARGIN.left} x2={right} y1={axis.y(value)} y2={axis.y(value)} />
            {axis.labelled(value) && (
              <text className={styles.label} x={MARGIN.left - 6} y={axis.y(value) + 4} textAnchor="end">{value}</text>
            )}
          </g>
        ))}
        {ticks.filter(isDay).map((ms) => (
          <line key={ms} className={styles.grid} x1={x(ms)} x2={x(ms)} y1={MARGIN.top} y2={bottom} />
        ))}
        {runs.map((run) => (
          <path key={run[0].time.getTime()} className={styles.area}
            d={`M${edge(run[0])},${baseline.toFixed(1)} L${points(run)} L${edge(run[run.length - 1])},${baseline.toFixed(1)} Z`} />
        ))}
        {runs.map((run) => (
          <path key={run[0].time.getTime()} className={styles.line} d={`M${points(run)}`} />
        ))}
        <line className={styles.axis} x1={MARGIN.left} x2={right} y1={bottom} y2={bottom} />
        <line className={styles.axis} x1={MARGIN.left} x2={MARGIN.left} y1={MARGIN.top} y2={bottom} />
        {ticks.map((ms) => (
          <line key={ms} className={styles.axis} x1={x(ms)} x2={x(ms)} y1={bottom} y2={bottom + (isDay(ms) ? 6 : 3)} />
        ))}
        {ticks.filter(isDay).map((ms) => (
          <text key={ms} className={styles.label} x={Math.min(x(ms), width - DAY_LABEL_HALF_WIDTH)} y={bottom + 19}
            textAnchor="middle">{dayLabel(new Date(ms), withYear)}</text>
        ))}
        <line className={styles.now} x1={right} x2={right} y1={MARGIN.top} y2={bottom} />
        <text className={styles.nowLabel} textAnchor="middle" transform={`translate(${right + 15} ${(MARGIN.top + bottom) / 2}) rotate(-90)`}>
          aktuell {utcClock(series.end)} UTC
        </text>
        {measured.map((sample) => (
          <rect key={sample.time.getTime()} className={styles.hit} x={x(sample.time.getTime()) - columnWidth / 2}
            y={MARGIN.top} width={columnWidth} height={bottom - MARGIN.top}>
            <title>{tooltip(sample)}</title>
          </rect>
        ))}
      </>
    )
  }

  return (
    <div ref={box} className={styles.box}>
      {right > MARGIN.left && bottom > MARGIN.top && (
        <svg className={styles.svg} viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
          <text className={styles.title} x={width / 2} y={22} textAnchor="middle">
            {width >= NAMED_TITLE_WIDTH ? `${stationName} – Lufttemperatur` : 'Lufttemperatur'}
          </text>
          <line className={styles.line} x1={width / 2 - 62} x2={width / 2 - 36} y1={38} y2={38} />
          <text className={styles.label} x={width / 2 - 30} y={42}>Messwerte (10 min)</text>
          <text className={styles.label} textAnchor="middle" transform={`translate(14 ${(MARGIN.top + bottom) / 2}) rotate(-90)`}>
            Lufttemperatur [°C]
          </text>
          {measured.length > 0
            ? render()
            : <text className={styles.label} x={width / 2} y={height / 2} textAnchor="middle">keine Messwerte</text>}
        </svg>
      )}
    </div>
  )
}
