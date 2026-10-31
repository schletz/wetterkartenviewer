import type { CSSProperties } from 'react'
import { holidayName } from '../model/holidays'
import styles from './StepSlider.module.css'

export const MAX_STEP = 240
const HOUR_MS = 3_600_000
const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

interface StepSliderProps {
  step: number
  /** Base time of the run the steps count from. */
  runTime: Date
  onChange: (step: number) => void
}

/** Valid time of a step. */
function validTime(runTime: Date, step: number): Date {
  return new Date(runTime.getTime() + step * HOUR_MS)
}

/** Sunday or Austrian public holiday: shown in red, as in a calendar. */
function isRedDay(date: Date): boolean {
  return date.getUTCDay() === 0 || holidayName(date) !== undefined
}

/** "So, 1." for the day of a valid time (UTC); the month is clear within a 10-day forecast. */
function dayLabel(date: Date): string {
  return `${WEEKDAYS[date.getUTCDay()]}, ${date.getUTCDate()}.`
}

/** Steps at 00 UTC within the slider range: the day boundaries, whatever the run hour. */
function midnightSteps(runTime: Date): number[] {
  const first = (24 - runTime.getUTCHours()) % 24
  return Array.from({ length: Math.floor((MAX_STEP - first) / 24) + 1 }, (_, day) => first + day * 24)
}

/**
 * Forecast hour 0-240 in 1 h steps, labelled with the valid time in UTC ("So, 1. 00Z");
 * below the track the days at 00 UTC, Sundays and holidays in red.
 */
export default function StepSlider({ step, runTime, onChange }: StepSliderProps) {
  const valid = validTime(runTime, step)
  const midnights = midnightSteps(runTime)
  return (
    <div className={styles.slider}>
      <span className={`${styles.value} ${isRedDay(valid) ? styles.red : ''}`}
        title={`+${step} h${holidayName(valid) ? `, ${holidayName(valid)}` : ''}`}>
        {dayLabel(valid)} {String(valid.getUTCHours()).padStart(2, '0')}Z
      </span>
      <div className={styles.track}>
        <input className={styles.range} type="range" min={0} max={MAX_STEP} step={1} list="day-ticks"
          value={step} onChange={(e) => onChange(Number(e.target.value))} />
        <datalist id="day-ticks">
          {midnights.map((tick) => <option key={tick} value={tick} />)}
        </datalist>
        <div className={styles.days}>
          {midnights.map((tick) => {
            const day = validTime(runTime, tick)
            return (
              <span key={tick} className={`${styles.day} ${isRedDay(day) ? styles.red : ''}`}
                style={{ '--at': tick / MAX_STEP } as CSSProperties} title={holidayName(day)}
                onClick={() => onChange(tick)}>
                {dayLabel(day)}
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}
