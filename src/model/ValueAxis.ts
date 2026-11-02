/** Labels are at least this many pixels apart. */
const MIN_LABEL_SPACING = 22
/** Space between the extreme values and the plot edges, in units of the values. */
const PADDING = 0.5

/** Distances between labelled values for temperatures, K. */
export const TEMPERATURE_STEPS = [1, 2, 5, 10, 20, 50]
/** Distances between labelled values for thicknesses, dam: the 4 dam spacing of synoptic charts and multiples. */
export const THICKNESS_STEPS = [1, 2, 4, 8, 16, 32]

/** Vertical axis of one diagram panel: a range of round values mapped onto a pixel interval. */
export class ValueAxis {
  readonly min: number
  readonly max: number
  /** Distance between labelled values. */
  readonly step: number
  private readonly top: number
  private readonly bottom: number

  /**
   * @param values every value the panel shows; must not be empty
   * @param top pixel row of the top of the plot
   * @param bottom pixel row of the bottom of the plot
   * @param steps candidate label distances, ascending; the smallest that keeps the labels apart wins
   */
  constructor(values: number[], top: number, bottom: number, steps: readonly number[]) {
    const low = Math.min(...values) - PADDING
    const high = Math.max(...values) + PADDING
    const intervals = Math.max(1, Math.floor((bottom - top) / MIN_LABEL_SPACING))
    this.step = steps.find((s) => Math.ceil(high / s) - Math.floor(low / s) <= intervals) ?? steps[steps.length - 1]
    this.min = Math.floor(low / this.step) * this.step
    this.max = Math.ceil(high / this.step) * this.step
    this.top = top
    this.bottom = bottom
  }

  /** Pixel row of a value. */
  y(value: number): number {
    return this.bottom - ((value - this.min) / (this.max - this.min)) * (this.bottom - this.top)
  }

  /** Labelled values, every `step` from min to max. */
  ticks(): number[] {
    const ticks: number[] = []
    for (let value = this.min; value <= this.max + 1e-9; value += this.step) ticks.push(value)
    return ticks
  }
}
