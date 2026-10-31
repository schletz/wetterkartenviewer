import styles from './StepSlider.module.css'

export const MAX_STEP = 240
const DAY_TICKS = Array.from({ length: MAX_STEP / 24 + 1 }, (_, day) => day * 24)

interface StepSliderProps {
  step: number
  onChange: (step: number) => void
}

/** Forecast hour 0-240 in 1 h steps; the charts carry the valid time in their legend. */
export default function StepSlider({ step, onChange }: StepSliderProps) {
  return (
    <div className={styles.slider}>
      <span className={styles.value}>+{step} h</span>
      <input className={styles.range} type="range" min={0} max={MAX_STEP} step={1} list="day-ticks"
        value={step} onChange={(e) => onChange(Number(e.target.value))} />
      <datalist id="day-ticks">
        {DAY_TICKS.map((tick) => <option key={tick} value={tick} />)}
      </datalist>
    </div>
  )
}
