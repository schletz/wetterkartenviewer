/**
 * Areas between a T850 series and its climate mean, layered in steps of the standard deviation;
 * also areas beyond fixed thresholds (`thresholdPolygons`, the Showalter classes).
 *
 * Port of AnomalyBands of the synop skill (skills/synop/scripts/lib/anomaly_bands.py).
 * Knows nothing about SVG: vertices come as (x, value) and the caller maps them onto its drawing.
 */

export const WARM = 1
export const COLD = -1
export type Side = typeof WARM | typeof COLD

/** One valid time: horizontal position, T850, climate mean and standard deviation. */
export interface BandPoint {
  x: number
  value: number
  mean: number
  std: number
}

export interface BandPolygon {
  side: Side
  /** Along T850 and back along the threshold, as [x, value]. */
  vertices: [number, number][]
}

/** [x, value, threshold] */
type Sample = [number, number, number]

/**
 * Polygons of the parts of a series above mean + k σ (WARM) and below mean − k σ (COLD) for every k.
 *
 * Drawn on top of each other with some transparency, they shade the anomaly
 * darker with every σ. A null point breaks the areas.
 */
export function anomalyPolygons(points: (BandPoint | null)[], sigmaSteps: readonly number[]): BandPolygon[] {
  return sigmaSteps.flatMap((step) => ([WARM, COLD] as const).flatMap((side) =>
    polygonsBeyond(points.map((p): Sample | null => (p === null ? null : [p.x, p.value, p.mean + side * step * p.std])), side)))
}

/**
 * Polygons of the parts of a series above each threshold of `above` (WARM) and below each of `below` (COLD).
 *
 * Drawn like the anomaly layers, every further threshold shades darker. A null point breaks the areas.
 */
export function thresholdPolygons(points: ({ x: number; value: number } | null)[], above: readonly number[],
  below: readonly number[]): BandPolygon[] {
  const layers = [...above.map((threshold) => [WARM, threshold] as const), ...below.map((threshold) => [COLD, threshold] as const)]
  return layers.flatMap(([side, threshold]) =>
    polygonsBeyond(points.map((p): Sample | null => (p === null ? null : [p.x, p.value, threshold])), side))
}

/** Polygons along the series and back along its threshold, where it lies beyond the threshold on `side`. */
function polygonsBeyond(series: (Sample | null)[], side: Side): BandPolygon[] {
  return runsBeyond(series, side).map((run) => ({
    side,
    vertices: [
      ...run.map(([x, value]): [number, number] => [x, value]),
      ...[...run].reverse().map(([x, , threshold]): [number, number] => [x, threshold]),
    ],
  }))
}

function sign(value: number): number {
  return value > 0 ? 1 : value < 0 ? -1 : 0
}

/**
 * Runs of samples where the value lies beyond the threshold on `side`.
 *
 * A segment that crosses the threshold is split at the crossing, so the areas
 * end exactly there. Consecutive pieces on the same side form one run, which
 * avoids seams between adjacent polygons.
 */
function runsBeyond(series: (Sample | null)[], side: Side): Sample[][] {
  // The series with the crossings inserted; null breaks it.
  const points: (Sample | null)[] = []
  let previous: Sample | null = null
  for (const current of series) {
    if (current === null) {
      points.push(null)
      previous = null
      continue
    }
    if (previous !== null) {
      const before = previous[1] - previous[2]
      const after = current[1] - current[2]
      if (before * after < 0) {
        const share = before / (before - after)
        const value = previous[1] + share * (current[1] - previous[1])
        points.push([previous[0] + share * (current[0] - previous[0]), value, value])
      }
    }
    points.push(current)
    previous = current
  }

  const runs: Sample[][] = []
  let run: Sample[] = []
  let runSign = 0
  for (const point of [...points, null]) {
    const pointSign = point === null ? 0 : sign(point[1] - point[2])
    if (point === null || (pointSign !== 0 && runSign !== 0 && pointSign !== runSign)) {
      if (runSign === side && run.length >= 2) runs.push(run)
      // The next run starts at the crossing that ended this one.
      run = point === null ? [] : [run[run.length - 1]]
      runSign = 0
    }
    if (point !== null) {
      run.push(point)
      runSign = runSign || pointSign
    }
  }
  return runs
}
