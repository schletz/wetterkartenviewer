/** One temperature value with the time stamp of its 10 min interval. */
export interface TemperatureReading {
  /** Air temperature in °C. */
  value: number
  time: Date
}

/** Temperatures of one station since 00 UTC; each reading is null while the series holds no value at all. */
export interface DayTemperatures {
  /** Last non-null air temperature of the series. */
  current: TemperatureReading | null
  /** Lowest 10 min minimum (TLMIN), or the 10 min value (TL) where the minimum is missing. */
  min: TemperatureReading | null
  /** Highest 10 min maximum (TLMAX), or the 10 min value (TL) where the maximum is missing. */
  max: TemperatureReading | null
}

/**
 * Current value, minimum and maximum of the 10 min series of one station.
 * Missing values (null, e.g. the last interval before it was transmitted) are skipped;
 * on a tie the earliest time wins.
 *
 * @param timestamps ISO times of the intervals, one per array element
 * @param tl 10 min air temperature (TL)
 * @param tlmin minimum within each interval (TLMIN)
 * @param tlmax maximum within each interval (TLMAX)
 */
export function summarizeTemperatures(
  timestamps: string[], tl: (number | null)[], tlmin: (number | null)[], tlmax: (number | null)[],
): DayTemperatures {
  let current: TemperatureReading | null = null
  let min: TemperatureReading | null = null
  let max: TemperatureReading | null = null
  timestamps.forEach((stamp, i) => {
    const time = new Date(stamp)
    const value = tl[i] ?? null
    if (value !== null) current = { value, time }
    const low = tlmin[i] ?? value
    if (low !== null && (min === null || low < min.value)) min = { value: low, time }
    const high = tlmax[i] ?? value
    if (high !== null && (max === null || high > max.value)) max = { value: high, time }
  })
  return { current, min, max }
}
