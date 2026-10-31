/** A position in degrees north and east. */
export interface GeoLocation {
  lat: number
  lon: number
}

export const DEFAULT_LOCATION: GeoLocation = { lat: 48, lon: 16.4 }

/** True for a position that lies on the globe. */
export function isValidLocation(location: GeoLocation): boolean {
  return Number.isFinite(location.lat) && Number.isFinite(location.lon)
    && Math.abs(location.lat) <= 90 && Math.abs(location.lon) <= 180
}
