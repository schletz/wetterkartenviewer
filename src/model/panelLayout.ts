/**
 * Content and vertical layout of the panels of the temperature diagram
 * (components/TemperatureDiagram.tsx places them, components/TemperaturePanel.tsx draws one).
 */
import type { BandPolygon } from './anomalyBands'
import type { ColourBand } from './seriesFiles'
import type { ValuePoint } from './TemperatureSeries'

export const TITLE_HEIGHT = 16
export const LEGEND_LINE_HEIGHT = 14
/** Space between the legend and the plot. */
const HEADER_GAP = 6
/** Below the plot: tick marks and day labels. */
const TIME_AXIS_HEIGHT = 24
/** Height of a colour bar at the bottom of the plot; the value axis ends above it. */
export const COLOUR_BAR_HEIGHT = 10

/** A series of the panel; null breaks the line. */
export interface PanelLine {
  values: (ValuePoint | null)[]
  /** Colour and dash style, also of the legend swatch. */
  className: string
}

/**
 * A series without an axis of its own: `range(min, max)` gives, for the range of the panel's value axis, the values
 * of the series drawn at its bottom and top. Values beyond are clamped to the plot edges.
 */
export interface ScaledLine extends PanelLine {
  range: (min: number, max: number) => readonly [bottom: number, top: number]
}

/** Classes of layered areas: area above and below the line between them. */
export interface BandSwatchClasses {
  above: string
  below: string
  line: string
}

/**
 * A legend entry, one row each: a line swatch, or several line swatches stacked in one row (related series that
 * share one text, so the plot keeps its height).
 */
export type LegendEntry = { text: string } & ({ line: string } | { lines: string[] })

/**
 * A series shown as a strip of colours at the bottom of the plot, below the value axis: every value covers an interval
 * before its valid time (a maximum or a sum) and colours the time from the previous value to its own with its band.
 */
export interface ColourBar {
  values: ValuePoint[]
  colours: ColourBand[]
  /** Values below stay uncoloured; undefined colours every value. */
  transparentBelow?: number
}

/**
 * A signed series without an axis of its own, drawn around the middle of the panel's value axis: a zero line
 * there, layered areas above it (WARM) and below it (COLD). Only the class of the values counts, not the size.
 */
export interface CentredBands {
  /** Areas beyond thresholds, vertices as [x in px, value]. */
  polygons: BandPolygon[]
  /** Largest absolute value; sets how far the areas reach. */
  extent: number
  /** Axis units per unit of the values at most; less when the areas would leave the plot. */
  maxScale: number
  /** Area classes above (WARM) and below (COLD) zero, and the class of the zero line. */
  classes: BandSwatchClasses
}

/** Content of one panel; the lines are drawn in order, so the last lies on top. */
export interface PanelSpec {
  key: string
  title: string
  legend: LegendEntry[]
  lines: PanelLine[]
  /** Series without an axis of their own, drawn below `lines`; they do not widen the axis. */
  scaledLines?: ScaledLine[]
  /** Anomaly areas below the lines, vertices as [x in px, value]. */
  bands?: BandPolygon[]
  /** Signed areas around the middle of the axis, below the lines. */
  centred?: CentredBands
  /** Strip of colours at the bottom of the plot; the value axis ends above it. */
  colourBar?: ColourBar
  /** Label distances of the value axis. */
  steps: readonly number[]
  /** Share of the height the plots split among themselves. */
  weight: number
}

/** The time range all panels share, in ms since the epoch. */
export interface TimeAxis {
  start: number
  end: number
  /** 00 UTC of every day from the one of `start` on. */
  days: number[]
  /** Tick marks, every few hours. */
  ticks: number[]
  x: (time: Date | number) => number
}

/** A panel and its pixel rows: title at `top`, plot from `plotTop` to `plotBottom`, day labels down to `bottom`. */
export interface PlacedPanel {
  panel: PanelSpec
  top: number
  bottom: number
  plotTop: number
  plotBottom: number
}

/** Pixels a panel needs besides its plot. */
function overhead(panel: PanelSpec): number {
  return TITLE_HEIGHT + panel.legend.length * LEGEND_LINE_HEIGHT + HEADER_GAP + TIME_AXIS_HEIGHT
}

/**
 * Stacks the panels from `top` down to `height`, `gap` apart: every panel gets its fixed rows
 * (title, legend, day labels), the plots share the rest by weight.
 */
export function placePanels(panels: PanelSpec[], top: number, height: number, gap: number): PlacedPanel[] {
  const fixed = top + panels.reduce((sum, panel) => sum + overhead(panel), 0) + gap * (panels.length - 1)
  const perWeight = Math.max(0, height - fixed) / panels.reduce((sum, panel) => sum + panel.weight, 0)
  const placed: PlacedPanel[] = []
  let panelTop = top
  for (const panel of panels) {
    const bottom = panelTop + overhead(panel) + panel.weight * perWeight
    placed.push({
      panel,
      top: panelTop,
      bottom,
      plotTop: panelTop + overhead(panel) - TIME_AXIS_HEIGHT,
      plotBottom: bottom - TIME_AXIS_HEIGHT,
    })
    panelTop = bottom + gap
  }
  return placed
}
