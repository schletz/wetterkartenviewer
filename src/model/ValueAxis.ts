/** Labels are at least this many pixels apart. */
const MIN_LABEL_SPACING = 22
/** Space between the extreme values and the plot edges of a fitted axis, in units of the values. */
const PADDING = 0.5
/** Every how many grid lines a label may sit, smallest first: used when the plot is too low to label each one. */
const LABEL_EVERY = [1, 2, 4]

/** Distances between labelled values for thicknesses, dam: the 4 dam spacing of synoptic charts and multiples. */
export const THICKNESS_STEPS = [1, 2, 4, 8, 16, 32]

/**
 * How a panel chooses its value range.
 * - `fitted`: the smallest step of `steps` whose labels stay apart, range rounded outward to it.
 * - `fixed`: always `step` between grid lines, at least `minSpan` from bottom to top, so a calm period
 *   (stable weather) does not blow small changes up to the full plot height.
 */
export type AxisScale =
  | { kind: 'fitted'; steps: readonly number[] }
  | { kind: 'fixed'; step: number; minSpan: number }

/** Temperature panels: 5 K grid, at least 20 K range. */
export const TEMPERATURE_SCALE: AxisScale = { kind: 'fixed', step: 5, minSpan: 20 }
/** Thickness panel: fitted to its values. */
export const THICKNESS_SCALE: AxisScale = { kind: 'fitted', steps: THICKNESS_STEPS }

/** Vertical axis of one diagram panel: a range of round values mapped onto a pixel interval. */
export class ValueAxis {
  readonly min: number
  readonly max: number
  /** Distance between grid lines. */
  readonly step: number
  /** Every how many grid lines a label sits. */
  private readonly labelEvery: number
  private readonly top: number
  private readonly bottom: number

  /**
   * @param values every value the panel shows; must not be empty
   * @param top pixel row of the top of the plot
   * @param bottom pixel row of the bottom of the plot
   * @param scale how the range is chosen, see {@link AxisScale}
   */
  constructor(values: number[], top: number, bottom: number, scale: AxisScale) {
    const low = Math.min(...values)
    const high = Math.max(...values)
    const range = scale.kind === 'fitted' ? fittedRange(low, high, top, bottom, scale.steps) : fixedRange(low, high, scale)
    this.min = range.min
    this.max = range.max
    this.step = range.step
    const spacing = (bottom - top) / ((this.max - this.min) / this.step)
    this.labelEvery = LABEL_EVERY.find((every) => every * spacing >= MIN_LABEL_SPACING) ?? LABEL_EVERY[LABEL_EVERY.length - 1]
    this.top = top
    this.bottom = bottom
  }

  /** Pixel row of a value. */
  y(value: number): number {
    return this.bottom - ((value - this.min) / (this.max - this.min)) * (this.bottom - this.top)
  }

  /** Grid lines, every `step` from min to max. */
  ticks(): number[] {
    const ticks: number[] = []
    for (let value = this.min; value <= this.max + 1e-9; value += this.step) ticks.push(value)
    return ticks
  }

  /** Whether a grid line carries a label: all of them, or only multiples of a larger distance on a low plot. */
  labelled(value: number): boolean {
    return Math.abs(Math.round(value / this.step)) % this.labelEvery === 0
  }
}

interface Range {
  min: number
  max: number
  step: number
}

/**
 * Range of all values ± PADDING, rounded outward to the smallest step that keeps the labels apart.
 * If none does (plot too low), the step with the fewest intervals wins, the smallest of them on a tie:
 * a range across 0 needs at least two intervals with any step, so −20…20 beats −50…50.
 */
function fittedRange(low: number, high: number, top: number, bottom: number, steps: readonly number[]): Range {
  const from = low - PADDING
  const to = high + PADDING
  const intervals = Math.max(1, Math.floor((bottom - top) / MIN_LABEL_SPACING))
  const count = (step: number) => Math.ceil(to / step) - Math.floor(from / step)
  // reduce keeps the earlier (smaller) step on a tie because steps are ascending
  const step =
    steps.find((candidate) => count(candidate) <= intervals) ??
    steps.reduce((best, candidate) => (count(candidate) < count(best) ? candidate : best))
  return { min: Math.floor(from / step) * step, max: Math.ceil(to / step) * step, step }
}

/**
 * Bottom = the grid line at or below the lowest value, top = the first grid line above the highest value
 * (always some room on top). A range below `minSpan` grows one step at a time on the side with less room
 * between the values and the edge, so the values stay about centred.
 */
function fixedRange(low: number, high: number, { step, minSpan }: { step: number; minSpan: number }): Range {
  let min = Math.floor(low / step) * step
  let max = (Math.floor(high / step) + 1) * step
  while (max - min < minSpan - 1e-9) {
    if (max - high <= low - min) max += step
    else min -= step
  }
  return { min, max, step }
}
