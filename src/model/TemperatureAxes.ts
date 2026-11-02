/** Height of the 850 hPa surface in the ICAO standard atmosphere, m. */
export const HEIGHT_850 = 1457
/** Dry adiabatic lapse rate, rounded to 1 K per 100 m. */
export const LAPSE_RATE = 0.01
/**
 * Coupling of the thickness axis to the T850 axis, as in the synop skill (coupled_axes.py):
 * thickness = 544 dam + 1.6 dam/K · T850, so both lines lie on top of each other for typical
 * central European air masses; where they part, the column is colder or warmer than 850 hPa suggests.
 */
export const THICKNESS_AT_ZERO = 544
export const THICKNESS_PER_KELVIN = 1.6
/** Candidate spacings of the thickness labels, dam; the first with at most MAX_THICKNESS_TICKS intervals wins. */
const THICKNESS_STEPS = [4, 8, 16, 32]
const MAX_THICKNESS_TICKS = 12

/**
 * Three vertical axes of one scale: T2m on the left, T850 and the 1000–500 hPa thickness on the right.
 *
 * The T850 axis is shifted by the dry adiabatic warming from 850 hPa down to
 * the height of the location, so T850 and T2m lie on top of each other when
 * the air is mixed down to the ground; a T2m line below the T850 line shows an
 * inversion or radiative cooling. The thickness axis is coupled to the T850 axis.
 */
export class TemperatureAxes {
  /** T2m axis value at the height of T850 axis value 0, K. */
  readonly offset: number
  /** Range of the T2m axis, °C. */
  readonly min: number
  readonly max: number
  /** Distance between labelled values, K. */
  readonly step: number
  private readonly top: number
  private readonly bottom: number

  /**
   * @param t2m every T2m value to show, °C
   * @param t850 every T850 value to show (forecast and climate), °C
   * @param thickness every thickness value to show, dam
   * @param height height of the location, m
   * @param top pixel row of the top of the plot
   * @param bottom pixel row of the bottom of the plot
   */
  constructor(t2m: number[], t850: number[], thickness: number[], height: number, top: number, bottom: number) {
    this.offset = (HEIGHT_850 - height) * LAPSE_RATE
    const values = [...t2m, ...[...t850, ...thickness.map(thicknessToT850)].map((value) => value + this.offset)]
    const low = Math.min(...values) - 1
    const high = Math.max(...values) + 1
    const span = high - low
    this.step = span <= 16 ? 2 : span <= 40 ? 5 : 10
    this.min = Math.floor(low / this.step) * this.step
    this.max = Math.ceil(high / this.step) * this.step
    this.top = top
    this.bottom = bottom
  }

  /** Pixel row of a T2m value. */
  y2m(value: number): number {
    return this.bottom - ((value - this.min) / (this.max - this.min)) * (this.bottom - this.top)
  }

  /** Pixel row of a T850 value. */
  y850(value: number): number {
    return this.y2m(value + this.offset)
  }

  /** Pixel row of a thickness value in dam. */
  yThickness(value: number): number {
    return this.y850(thicknessToT850(value))
  }

  /** Labelled T2m values, every `step` from min to max. */
  ticks2m(): number[] {
    return range(this.min, this.max, this.step)
  }

  /** Labelled T850 values: round values every `step` inside the shifted range. */
  ticks850(): number[] {
    const low = Math.ceil((this.min - this.offset) / this.step) * this.step
    return range(low, this.max - this.offset, this.step)
  }

  /** Labelled thickness values: multiples of the coarsest fitting step; 1.6 dam/K rarely gives round dam at round K. */
  ticksThickness(): number[] {
    const low = THICKNESS_AT_ZERO + THICKNESS_PER_KELVIN * (this.min - this.offset)
    const high = THICKNESS_AT_ZERO + THICKNESS_PER_KELVIN * (this.max - this.offset)
    const step = THICKNESS_STEPS.find((s) => (high - low) / s <= MAX_THICKNESS_TICKS) ?? THICKNESS_STEPS[THICKNESS_STEPS.length - 1]
    return range(Math.ceil(low / step - 1e-9) * step, high, step)
  }
}

/** T850 value at the height of a thickness value on the coupled axes. */
function thicknessToT850(thickness: number): number {
  return (thickness - THICKNESS_AT_ZERO) / THICKNESS_PER_KELVIN
}

function range(from: number, to: number, step: number): number[] {
  const values: number[] = []
  for (let value = from; value <= to + 1e-9; value += step) values.push(value)
  return values
}
