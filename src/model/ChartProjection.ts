import type { GeoLocation } from './GeoLocation'

/** Size of every chart image: 1200x600 px map area plus a 90 px legend strip. */
export const IMAGE_WIDTH = 1200
export const IMAGE_HEIGHT = 690
export const MAP_HEIGHT = 600

/**
 * Pixel geometry of a chart window, the same model as scripts/lib/projection.py:
 * a conformal conic projection whose central meridian lon0 runs vertically through
 * the apex (poleX, poleY), origin top left, y pointing down. cone = 1 is the polar
 * stereographic projection of the ECMWF open charts windows, 0 < cone < 1 Lambert's.
 *
 *     rho = scaleK * tan(45 deg - lat / 2) ** cone
 *     x   = poleX + rho * sin(cone * (lon - lon0))
 *     y   = poleY + rho * cos(cone * (lon - lon0))
 */
export class ChartProjection {
  readonly poleX: number
  readonly poleY: number
  readonly scaleK: number
  readonly cone: number
  readonly lon0: number

  constructor(poleX: number, poleY: number, scaleK: number, cone = 1, lon0 = 0) {
    this.poleX = poleX
    this.poleY = poleY
    this.scaleK = scaleK
    this.cone = cone
    this.lon0 = lon0
  }

  /** Image pixel of a position, or null when it falls outside the map area. */
  toPixel(location: GeoLocation): { x: number; y: number } | null {
    const rad = Math.PI / 180
    const rho = this.scaleK * Math.tan((45 - location.lat / 2) * rad) ** this.cone
    // Longitude relative to the central meridian in -180..180, as in projection.py.
    const theta = this.cone * ((((location.lon - this.lon0 + 180) % 360) + 360) % 360 - 180) * rad
    const x = this.poleX + rho * Math.sin(theta)
    const y = this.poleY + rho * Math.cos(theta)
    return x >= 0 && x < IMAGE_WIDTH && y >= 0 && y < MAP_HEIGHT ? { x, y } : null
  }
}

/** Parameters as in scripts/lib/projection.py (and data/<window>/geometry.json). */
const PROJECTIONS: Record<string, ChartProjection> = {
  opencharts_europe: new ChartProjection(481.0, -180.8, 1320.8),
  opencharts_central_europe: new ChartProjection(435.35, -1021.0, 3493.4),
  'icon-d2': new ChartProjection(733.2439628710566, -7464.407027195254, 15611.893414386514, 0.7373615976163657,
    13.333333333333334),
}

/** Projection of a chart path "window/product", or null for an unknown window. */
export function projectionOf(chartPath: string): ChartProjection | null {
  return PROJECTIONS[chartPath.split('/')[0]] ?? null
}
