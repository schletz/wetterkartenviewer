import type { GeoLocation } from './GeoLocation'

/** Size of every chart image: 1200x600 px map area plus a 90 px legend strip. */
export const IMAGE_WIDTH = 1200
export const IMAGE_HEIGHT = 690
export const MAP_HEIGHT = 600

/**
 * Pixel geometry of an ECMWF open charts window, the same model as
 * scripts/lib/projection.py: a polar stereographic projection
 * with a vertical zero meridian, origin top left, y pointing down.
 *
 *     rho = scaleK * tan(45 deg - lat / 2)
 *     x   = poleX + rho * sin(lon)
 *     y   = poleY + rho * cos(lon)
 */
export class ChartProjection {
  readonly poleX: number
  readonly poleY: number
  readonly scaleK: number

  constructor(poleX: number, poleY: number, scaleK: number) {
    this.poleX = poleX
    this.poleY = poleY
    this.scaleK = scaleK
  }

  /** Image pixel of a position, or null when it falls outside the map area. */
  toPixel(location: GeoLocation): { x: number; y: number } | null {
    const rad = Math.PI / 180
    const rho = this.scaleK * Math.tan((45 - location.lat / 2) * rad)
    const x = this.poleX + rho * Math.sin(location.lon * rad)
    const y = this.poleY + rho * Math.cos(location.lon * rad)
    return x >= 0 && x < IMAGE_WIDTH && y >= 0 && y < MAP_HEIGHT ? { x, y } : null
  }
}

const PROJECTIONS: Record<string, ChartProjection> = {
  opencharts_europe: new ChartProjection(481.0, -180.8, 1320.8),
  opencharts_central_europe: new ChartProjection(435.35, -1021.0, 3493.4),
}

/** Projection of a chart path "window/product", or null for an unknown window. */
export function projectionOf(chartPath: string): ChartProjection | null {
  return PROJECTIONS[chartPath.split('/')[0]] ?? null
}
