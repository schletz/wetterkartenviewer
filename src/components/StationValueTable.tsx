import { useLayoutEffect, useRef } from 'react'
import { hourlySamples, latestMeasurement, type TemperatureSample } from '../model/stationSeries'
import { temperatureColour } from '../model/temperatureBands'
import styles from './StationValueTable.module.css'

interface StationValueTableProps {
  samples: TemperatureSample[]
}

/** Local time of the browser. */
const TIME_FORMAT = new Intl.DateTimeFormat('de-AT', {
  day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})

const VALUE_FORMAT = new Intl.NumberFormat('de-AT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** „07.11 18:00“ in local time. */
function localStamp(time: Date): string {
  const part = (type: Intl.DateTimeFormatPartTypes) => TIME_FORMAT.formatToParts(time).find((p) => p.type === type)?.value
  return `${part('day')}.${part('month')} ${part('hour')}:${part('minute')}`
}

/** Table cell with the value on the colour of its temperature class. */
function ValueCell({ value }: { value: number | null }) {
  return (
    <td className={styles.value} style={{ background: temperatureColour(value) }}>
      {value === null ? '–' : `${VALUE_FORMAT.format(value)} °C`}
    </td>
  )
}

/**
 * The values at the full hours in local time, oldest first, and the latest measurement as the last row.
 * Mounted once per station with its data: it starts scrolled to the newest values and later reloads
 * leave the position alone.
 */
export default function StationValueTable({ samples }: StationValueTableProps) {
  const scroller = useRef<HTMLDivElement>(null)
  const hourly = hourlySamples(samples)
  const latest = latestMeasurement(samples)

  useLayoutEffect(() => {
    const element = scroller.current
    if (element) element.scrollTop = element.scrollHeight
  }, [])

  return (
    <div ref={scroller} className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Zeitpunkt</th>
            <th>Wert</th>
          </tr>
        </thead>
        <tbody>
          {hourly.map(({ time, value }) => (
            <tr key={time.getTime()}>
              <td className={styles.time}>{localStamp(time)}</td>
              <ValueCell value={value} />
            </tr>
          ))}
          {latest && (
            <tr>
              <td className={styles.time}>letzter Wert von:<br />{localStamp(latest.time)}</td>
              <ValueCell value={latest.value} />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
