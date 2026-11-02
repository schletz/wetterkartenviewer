import { anomalyPolygons, WARM } from '../model/anomalyBands'
import type { GeoLocation } from '../model/GeoLocation'
import { holidayName } from '../model/holidays'
import {
  HEIGHT_850, LAPSE_RATE, TemperatureAxes, THICKNESS_AT_ZERO, THICKNESS_PER_KELVIN,
} from '../model/TemperatureAxes'
import type { LocationTemperatures, ValuePoint } from '../model/TemperatureSeries'
import styles from './TemperatureDiagram.module.css'

const WIDTH = 1000
const HEIGHT = 340
const PLOT_LEFT = 52
// Right of the plot two label columns: T850, then the thickness.
const PLOT_RIGHT = WIDTH - 100
const THICKNESS_LABEL_X = PLOT_RIGHT + 56
const PLOT_TOP = 24
const PLOT_BOTTOM = HEIGHT - 44
/** Anomaly layers k: areas beyond mean ± k σ, each adding the same shade (as in the synop skill). */
const SIGMA_STEPS = [0, 1, 2, 3] as const
const TICK_HOURS = 3
const MIN_DAY_LABEL_WIDTH = 40
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

/** "Mo 2.11." of a UTC day. */
function dayLabel(day: Date): string {
  return `${WEEKDAYS[day.getUTCDay()]} ${day.getUTCDate()}.${day.getUTCMonth() + 1}.`
}

/**
 * SVG diagram of T850 with its anomaly against the ERA5 climate, T2m of ECMWF and ICON-D2 and the
 * 1000–500 hPa thickness; T2m and T850 axes are shifted by the dry adiabatic warming between 850 hPa
 * and the model height, the thickness axis is coupled to the T850 axis.
 */
export default function TemperatureDiagram({ temperatures }: TemperatureDiagramProps) {
  const { t850, climate850, t2mEcmwf, t2mIcon, thickness, height } = temperatures
  const start = t850.values[0].valid.getTime()
  const end = t850.values[t850.values.length - 1].valid.getTime()
  const x = (time: Date | number) => PLOT_LEFT + ((+time - start) / (end - start)) * (PLOT_RIGHT - PLOT_LEFT)
  const inRange = (point: ValuePoint) => +point.valid >= start && +point.valid <= end

  const icon = t2mIcon?.values.filter(inRange) ?? []
  const climateMeans = climate850.flatMap((c) => (c === null ? [] : [c.mean]))
  const axes = new TemperatureAxes([...t2mEcmwf.values, ...icon].map((p) => p.value),
    [...t850.values.map((p) => p.value), ...climateMeans], thickness?.values.map((p) => p.value) ?? [],
    height, PLOT_TOP, PLOT_BOTTOM)

  const path = (points: (ValuePoint | null)[], y: (value: number) => number) => {
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
  const climateLine = t850.values.map((p, i) => {
    const climate = climate850[i]
    return climate === null ? null : { valid: p.valid, value: climate.mean }
  })
  const bands = anomalyPolygons(t850.values.map((p, i) => {
    const climate = climate850[i]
    return climate === null ? null : { x: x(p.valid), value: p.value, mean: climate.mean, std: climate.std }
  }), SIGMA_STEPS)

  // Days from 00 UTC of the first valid time; 3-hourly ticks, longer at 12 and 00 UTC.
  const firstDay = Math.floor(start / (24 * HOUR_MS)) * 24 * HOUR_MS
  const days: number[] = []
  for (let day = firstDay; day <= end; day += 24 * HOUR_MS) days.push(day)
  const ticks: number[] = []
  for (let tick = firstDay; tick <= end; tick += TICK_HOURS * HOUR_MS) if (tick >= start) ticks.push(tick)

  const iconByTime = new Map(icon.map((p) => [+p.valid, p.value]))
  const ecmwfByTime = new Map(t2mEcmwf.values.map((p) => [+p.valid, p.value]))
  const thicknessByTime = new Map(thickness?.values.map((p) => [+p.valid, p.value]) ?? [])
  const columns = t850.values.map((p) => x(p.valid))
  const tooltip = (point: ValuePoint, i: number) => {
    const parts = [`${dayLabel(point.valid)} ${String(point.valid.getUTCHours()).padStart(2, '0')} UTC`,
      `T850 ${decimals(point.value, 1)} °C`]
    const climate = climate850[i]
    if (climate !== null) {
      parts.push(`Ø ${decimals(climate.mean, 1)} °C`)
      if (climate.std > 0) parts.push(`${(point.value - climate.mean) / climate.std >= 0 ? '+' : ''}${decimals((point.value - climate.mean) / climate.std, 1)} σ`)
    }
    const ecmwf = ecmwfByTime.get(+point.valid)
    if (ecmwf !== undefined) parts.push(`T2m ECMWF ${decimals(ecmwf, 1)} °C`)
    const iconValue = iconByTime.get(+point.valid)
    if (iconValue !== undefined) parts.push(`T2m ICON-D2 ${decimals(iconValue, 1)} °C`)
    const thicknessValue = thicknessByTime.get(+point.valid)
    if (thicknessValue !== undefined) parts.push(`Z1000–500 ${decimals(thicknessValue, 1)} dam`)
    return parts.join(' · ')
  }

  const offset = decimals(axes.offset, 1)
  return (
    <div className={styles.diagram}>
      <svg className={styles.svg} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img"
        aria-label="T2m von ECMWF und ICON-D2, T850 von ECMWF mit Abweichung vom Klimamittel">
        <defs>
          <clipPath id="temperature-plot">
            <rect x={PLOT_LEFT} y={PLOT_TOP} width={PLOT_RIGHT - PLOT_LEFT} height={PLOT_BOTTOM - PLOT_TOP} />
          </clipPath>
        </defs>
        <text className={styles.axisTitle} x={PLOT_LEFT} y={PLOT_TOP - 10} textAnchor="middle">T2m °C</text>
        <text className={styles.axisTitle} x={PLOT_RIGHT + 4} y={PLOT_TOP - 10}>T850 °C</text>
        {thickness !== null && <text className={styles.axisTitle} x={THICKNESS_LABEL_X} y={PLOT_TOP - 10}>dam</text>}
        {axes.ticks2m().map((value) => (
          <g key={`l${value}`}>
            <line className={value === 0 ? styles.zero : styles.grid} x1={PLOT_LEFT} x2={PLOT_RIGHT}
              y1={axes.y2m(value)} y2={axes.y2m(value)} />
            <text x={PLOT_LEFT - 8} y={axes.y2m(value) + 4} textAnchor="end">{value}</text>
          </g>
        ))}
        {axes.ticks850().map((value) => (
          <text key={`r${value}`} x={PLOT_RIGHT + 8} y={axes.y850(value) + 4}>{value}</text>
        ))}
        {thickness !== null && axes.ticksThickness().map((value) => (
          <text key={`z${value}`} className={styles.thicknessLabel} x={THICKNESS_LABEL_X}
            y={axes.yThickness(value) + 4}>{value}</text>
        ))}
        {days.map((day) => {
          const date = new Date(day)
          const left = x(Math.max(day, start))
          const right = x(Math.min(day + 24 * HOUR_MS, end))
          const red = date.getUTCDay() === 0 || holidayName(date) !== undefined
          return (
            <g key={day}>
              {day >= start && <line className={styles.grid} x1={x(day)} x2={x(day)} y1={PLOT_TOP} y2={PLOT_BOTTOM} />}
              {right - left >= MIN_DAY_LABEL_WIDTH && (
                <text className={red ? styles.holiday : undefined} x={(left + right) / 2} y={PLOT_BOTTOM + 30}
                  textAnchor="middle">{dayLabel(date)}<title>{holidayName(date)}</title></text>
              )}
            </g>
          )
        })}
        <line className={styles.axis} x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM} />
        {ticks.map((tick) => {
          const hour = new Date(tick).getUTCHours()
          return <line key={tick} className={styles.axis} x1={x(tick)} x2={x(tick)} y1={PLOT_BOTTOM}
            y2={PLOT_BOTTOM + (hour === 0 ? 10 : hour === 12 ? 7 : 4)} />
        })}
        <text x={PLOT_RIGHT + 8} y={PLOT_BOTTOM + 30}>UTC</text>
        <g clipPath="url(#temperature-plot)">
          {/* Anomaly areas and climate mean underneath, the T850 line on top of them. */}
          {bands.map((band, i) => (
            <polygon key={i} className={band.side === WARM ? styles.warm : styles.cold}
              points={band.vertices.map(([vx, value]) => `${vx.toFixed(1)},${axes.y850(value).toFixed(1)}`).join(' ')} />
          ))}
          <path className={`${styles.line} ${styles.climate}`} d={path(climateLine, (v) => axes.y850(v))} />
          <path className={`${styles.line} ${styles.t2mEcmwf}`} d={path(t2mEcmwf.values, (v) => axes.y2m(v))} />
          {icon.length > 0 && <path className={`${styles.line} ${styles.t2mIcon}`} d={path(icon, (v) => axes.y2m(v))} />}
          {thickness !== null && (
            <path className={`${styles.line} ${styles.thickness}`} d={path(thickness.values, (v) => axes.yThickness(v))} />
          )}
          <path className={`${styles.line} ${styles.t850}`} d={path(t850.values, (v) => axes.y850(v))} />
        </g>
        {t850.values.map((point, i) => {
          // Each hover column reaches halfway to its neighbours, so the 3 h and 6 h steps cover the plot without gaps.
          const left = i === 0 ? PLOT_LEFT : (columns[i - 1] + columns[i]) / 2
          const right = i === columns.length - 1 ? PLOT_RIGHT : (columns[i] + columns[i + 1]) / 2
          return (
            <g key={+point.valid} className={styles.hit}>
              <title>{tooltip(point, i)}</title>
              <rect x={left} y={PLOT_TOP} width={right - left} height={PLOT_BOTTOM - PLOT_TOP} />
              <line className={styles.cross} x1={columns[i]} x2={columns[i]} y1={PLOT_TOP} y2={PLOT_BOTTOM} />
            </g>
          )
        })}
      </svg>
      <ul className={styles.legend}>
        <li><span className={`${styles.swatch} ${styles.t850}`} />T850 ECMWF für {pointLabel(t850.point, t850.height)}</li>
        <li>
          <span className={styles.bands}>{SIGMA_STEPS.map((k) => <span key={k} className={styles.band} />)}</span>
          Ø {temperatures.period} (ERA5) für {pointLabel(temperatures.climatePoint)}, ±{SIGMA_STEPS.slice(1).join('/')} σ
        </li>
        <li><span className={`${styles.swatch} ${styles.t2mEcmwf}`} />T2m ECMWF für {pointLabel(t2mEcmwf.point, t2mEcmwf.height)}</li>
        {t2mIcon !== null && (
          <li><span className={`${styles.swatch} ${styles.t2mIcon}`} />T2m ICON-D2 für {pointLabel(t2mIcon.point, t2mIcon.height)}</li>
        )}
        {thickness !== null && (
          <li>
            <span className={`${styles.swatch} ${styles.thickness}`} />
            Schichtdicke 1000–500 hPa ECMWF für {pointLabel(thickness.point, thickness.height)}{' '}
            (dam, gekoppelt: {THICKNESS_AT_ZERO} + {decimals(THICKNESS_PER_KELVIN, 1)} · T850)
          </li>
        )}
        <li className={styles.note}>
          Modellhöhe {height} m (ICON-D2); T850-Achse um {offset} K verschoben
          ({decimals(LAPSE_RATE * 100, 0)} K/100 m ab {HEIGHT_850} m)
        </li>
      </ul>
    </div>
  )
}
