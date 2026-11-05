import type { ValuePoint } from './TemperatureSeries'

const HOUR_MS = 3_600_000
const DAY_MS = 24 * HOUR_MS
/**
 * Hours (UTC) whose values make up a daily mean, densest first: the IFS steps are 3-hourly up to +144 h and
 * 6-hourly beyond. Equally spaced samples weigh every part of the daily cycle alike; mixing both spacings on the
 * day of the change would overweight the 3-hourly part.
 */
const SAMPLE_HOURS: readonly (readonly number[])[] = [[0, 3, 6, 9, 12, 15, 18, 21], [0, 6, 12, 18]]

/**
 * Daily means of a series per UTC day: the mean of its values at the hours of the first set of `SAMPLE_HOURS` the
 * day holds completely. Days without one (the first day of a 12 UTC run, the last day, lost steps) are left out.
 * `valid` of each mean is 00 UTC of its day.
 */
export function dailyMeans(values: ValuePoint[]): ValuePoint[] {
  const days = new Map<number, Map<number, number>>()
  for (const { valid, value } of values) {
    if (valid.getUTCMinutes() !== 0) continue
    const day = Math.floor(valid.getTime() / DAY_MS) * DAY_MS
    const hours = days.get(day) ?? new Map<number, number>()
    hours.set(valid.getUTCHours(), value)
    days.set(day, hours)
  }
  return [...days].flatMap(([day, hours]) => {
    const sample = SAMPLE_HOURS.find((set) => set.every((hour) => hours.has(hour)))
    if (sample === undefined) return []
    const sum = sample.reduce((total, hour) => total + hours.get(hour)!, 0)
    return [{ valid: new Date(day), value: sum / sample.length }]
  })
}
