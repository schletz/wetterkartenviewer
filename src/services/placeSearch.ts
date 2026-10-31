import type { GeoLocation } from '../model/GeoLocation'

/** Geocoding service (OpenStreetMap) that resolves a place name. */
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'

/** A place found by name. */
export interface Place extends GeoLocation {
  /** Full name as nominatim gives it, e.g. "Innsbruck, Tirol, Österreich". */
  name: string
}

/** One entry of a nominatim search response. */
interface NominatimResult {
  lat: string
  lon: string
  display_name: string
}

/**
 * Resolves a place name (city, village, address) with nominatim and returns the first hit.
 *
 * @throws Error with a German message if the request fails or nothing is found.
 */
export async function searchPlace(query: string): Promise<Place> {
  const url = new URL(NOMINATIM_URL)
  url.search = new URLSearchParams({ q: query, format: 'jsonv2', limit: '1', 'accept-language': 'de' }).toString()
  const response = await fetch(url)
  if (!response.ok) throw new Error(`Ortssuche fehlgeschlagen (HTTP ${response.status})`)
  const results = (await response.json()) as NominatimResult[]
  const first = Array.isArray(results) ? results[0] : undefined
  if (!first) throw new Error(`„${query}“ nicht gefunden`)
  return { lat: parseFloat(first.lat), lon: parseFloat(first.lon), name: first.display_name }
}
