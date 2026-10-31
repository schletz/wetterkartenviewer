import { layerPaths, type ChartPath, type LayerConfig } from '../config/viewerConfig'

/** The video of one tile layer: one frame per forecast step, in step order. */
export interface ChartVideo {
  /** Path of the video relative to maps/. */
  file: string
  /** Forecast step of every frame, counted from the run of the manifest. */
  steps: number[]
  /** Run of the model the video comes from, YYYYMMDDHH in UTC; missing in older manifests. */
  run?: string
  /** Last step the video covers (hourly charts); later steps have no frame. */
  end?: number
}

/** The frame of a video that shows one forecast step. */
export interface ChartFrame {
  index: number
  step: number
}

/** maps/manifest.json as written by scripts/maps_manifest.py. */
export interface Manifest {
  /** Base time of the run, YYYYMMDDHH in UTC. */
  run: string
  /** Frames per second of every video; frame i covers [i / fps, (i + 1) / fps). */
  fps: number
  /** Video per chart path. */
  charts: Record<ChartPath, ChartVideo>
}

/** Looks up the videos and frames of one run. */
export class ChartIndex {
  private readonly manifest: Manifest

  constructor(manifest: Manifest) {
    this.manifest = manifest
  }

  get run(): string {
    return this.manifest.run
  }

  get fps(): number {
    return this.manifest.fps
  }

  /** Base time of the run as a Date. */
  get runTime(): Date {
    const r = this.manifest.run
    return new Date(Date.UTC(+r.slice(0, 4), +r.slice(4, 6) - 1, +r.slice(6, 8), +r.slice(8, 10)))
  }

  /** The latest frame at or before ``step``, or null if the product starts later, has ended or is missing. */
  frame(path: ChartPath, step: number): ChartFrame | null {
    const end = this.lastStep(path)
    if (end !== null && step > end) return null
    const steps = this.frameSteps(path)
    let index = -1
    while (index + 1 < steps.length && steps[index + 1] <= step) index++
    return index < 0 ? null : { index, step: steps[index] }
  }

  /** First step of a product, or null if the run has no video of it. */
  firstStep(path: ChartPath): number | null {
    return this.frameSteps(path)[0] ?? null
  }

  /** Last step a product covers, or null if it covers every later step. */
  lastStep(path: ChartPath): number | null {
    return this.manifest.charts[path]?.end ?? null
  }

  /** All steps that have a frame in any path of the given layers, sorted. */
  steps(layers: LayerConfig[]): number[] {
    const steps = new Set(layers.flatMap(layerPaths).flatMap((path) => this.frameSteps(path)))
    return [...steps].sort((a, b) => a - b)
  }

  /**
   * The chart path a layer shows at ``step``: the first of its paths with a frame there. Without
   * one, the last path with a video (or the last path), whose placeholder then tells why.
   */
  resolve(layer: LayerConfig, step: number): ChartPath {
    const paths = layerPaths(layer)
    return paths.find((path) => this.frame(path, step) !== null)
      ?? paths.findLast((path) => this.firstStep(path) !== null)
      ?? paths[paths.length - 1]
  }

  /**
   * URL of the video of a product relative to the page, or null if the run has none.
   * Every run reuses the file name; the run of the video's model in the query keeps the browser cache apart.
   */
  videoUrl(path: ChartPath): string | null {
    const video = this.manifest.charts[path]
    return video ? `${import.meta.env.BASE_URL}maps/${video.file}?run=${video.run ?? this.manifest.run}` : null
  }

  /** Time in seconds that shows a frame: its middle, so rounding never lands on the neighbour. */
  frameTime(frame: ChartFrame): number {
    return (frame.index + 0.5) / this.manifest.fps
  }

  private frameSteps(path: ChartPath): number[] {
    return this.manifest.charts[path]?.steps ?? []
  }
}
