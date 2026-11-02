import type { Manifest } from '../model/ChartIndex'

/** URL of a file below maps/, optionally with a cache parameter that changes with its content. */
export function mapsUrl(file: string, version?: string): string {
  const url = `${import.meta.env.BASE_URL}maps/${file}`
  return version === undefined ? url : `${url}?v=${encodeURIComponent(version)}`
}

/** Fetches maps/manifest.json; no-cache, because every run replaces it under the same name. */
export async function fetchManifest(signal: AbortSignal): Promise<Manifest> {
  const response = await fetch(mapsUrl('manifest.json'), { cache: 'no-cache', signal })
  if (!response.ok) throw new Error(`manifest.json: HTTP ${response.status}`)
  return response.json() as Promise<Manifest>
}
