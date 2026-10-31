import rawConfig from './viewer.config.json'

/** One chart path below maps/, e.g. "opencharts_europe/z500_t850" (window/product). */
export type ChartPath = string

/**
 * One layer of a tile: a chart path, or several in order of preference. Of several, each
 * step shows the first one that has a chart then, e.g. ICON-D2 for its 48 h and ECMWF after.
 */
export type LayerConfig = ChartPath | ChartPath[]

/** A tile shows one layer at a time; a left click switches to the next one. */
export interface TileConfig {
  layers: LayerConfig[]
}

/**
 * Settings edited by hand in viewer.config.json.
 * scripts/maps_manifest.py reads the same file to decide which charts are published.
 */
export interface ViewerConfig {
  /** ECMWF ENS meteogram names of the opencharts epsgrams API, shown on the start page. */
  meteograms: string[]
  tiles: TileConfig[]
}

/** The chart paths of a layer in order of preference. */
export function layerPaths(layer: LayerConfig): ChartPath[] {
  return typeof layer === 'string' ? [layer] : layer
}

export const viewerConfig: ViewerConfig = rawConfig
