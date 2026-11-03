/**
 * Content and vertical layout of the panels of the temperature diagram
 * (components/TemperatureDiagram.tsx places them, components/TemperaturePanel.tsx draws one).
 */
import type { BandPolygon } from './anomalyBands'
import type { ValuePoint } from './TemperatureSeries'

export const TITLE_HEIGHT = 16
export const LEGEND_LINE_HEIGHT = 14
/** Space between the legend and the plot. */
const HEADER_GAP = 6
/** Below the plot: tick marks and day labels. */
const TIME_AXIS_HEIGHT = 24

/** A series of the panel; null breaks the line. */
export interface PanelLine {
  values: (ValuePoint | null)[]
  /** Colour and dash style, also of the legend swatch. */
  className: string
}

/** A legend line: a line swatch, the anomaly shading, or the signed areas of `CentredBands`. */
export type LegendEntry = { text: string } & ({ line: string } | { bands: true } | { signs: true })

/**
 * A signed series without an axis of its own, drawn around the middle of the panel's value axis: a zero line
 * there, areas above it (WARM) and below it (COLD). Only the side counts, not the size.
 */
export interface CentredBands {
  /** Areas beyond zero, vertices as [x in px, value]. */
  polygons: BandPolygon[]
  /** Largest absolute value; sets how far the areas reach. */
  extent: number
  /** Axis units per unit of the values at most; less when the areas would leave the plot. */
  maxScale: number
}

/** Content of one panel; the lines are drawn in order, so the last lies on top. */
export interface PanelSpec {
  key: string
  title: string
  legend: LegendEntry[]
  lines: PanelLine[]
  /** Anomaly areas below the lines, vertices as [x in px, value]. */
  bands?: BandPolygon[]
  /** Signed areas around the middle of the axis, below the lines. */
  centred?: CentredBands
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
