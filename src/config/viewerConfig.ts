import rawConfig from './viewer.config.json'

/** One chart path below maps/, e.g. "opencharts_europe/z500_t850" (window/product). */
export type ChartPath = string

/** A tile shows one layer at a time; a left click switches to the next one. */
export interface TileConfig {
  layers: ChartPath[]
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

export const viewerConfig: ViewerConfig = rawConfig
