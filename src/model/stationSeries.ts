/** Full UTC days shown before the current UTC day. */
const FULL_DAYS = 3

/** One 10 min slot of a station; `value` is null while the station has not delivered it. */
export interface TemperatureSample {
  time: Date
  /** Air temperature in °C. */
  value: number | null
}

/** A slot that holds a measurement. */
export type MeasuredSample = TemperatureSample & { value: number }

/** 10 min air temperature of one station over the time span of the station viewer. */
export interface StationSeries {
  /** Start of the time axis: 00 UTC, `FULL_DAYS` before the current UTC day. */
  start: Date
  /** End of the time axis: the moment of the request. */
  end: Date
  samples: TemperatureSample[]
}

/** 00 UTC of the first day shown, e.g. 2026-11-05T00:00Z for 2026-11-08T07:40Z. */
export function seriesStart(now: Date): Date {
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - FULL_DAYS))
}

function isMeasured(sample: TemperatureSample): sample is MeasuredSample {
  return sample.value !== null
}

/** Latest slot that holds a measurement; null for a series without any. */
export function latestMeasurement(samples: TemperatureSample[]): MeasuredSample | null {
  return samples.findLast(isMeasured) ?? null
}

/**
 * The slots at a full hour of the local time zone, up to the latest measurement:
 * a null before it is a real gap of the station, a null after it is only not transmitted yet.
 */
export function hourlySamples(samples: TemperatureSample[]): TemperatureSample[] {
  const latest = latestMeasurement(samples)
  if (latest === null) return []
  return samples.filter(({ time }) => time.getMinutes() === 0 && time <= latest.time)
}

/** Unbroken runs of measurements; a slot without value ends a run, so lines and areas leave a gap there. */
export function measuredRuns(samples: TemperatureSample[]): MeasuredSample[][] {
  const runs: MeasuredSample[][] = []
  let run: MeasuredSample[] = []
  for (const sample of samples) {
    if (isMeasured(sample)) {
      run.push(sample)
    } else if (run.length > 0) {
      runs.push(run)
      run = []
    }
  }
  if (run.length > 0) runs.push(run)
  return runs
}
