import type { GeoLocation } from '../model/GeoLocation'

const EPSGRAM_API = 'https://charts.ecmwf.int/opencharts-api/v1/features/epsgrams/'
const ATTEMPTS = 5
const RETRY_MS = 3000

/** Answer of the epsgrams API; ``result`` is missing while the image is still being rendered. */
interface EpsgramResponse {
  result?: { url: string }
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(signal.reason)
    }, { once: true })
  })
}

/**
 * Asks ECMWF open charts to render an ENS meteogram for a location and
 * returns the URL of the image. The image itself exists only after this
 * request, so it cannot be linked directly. A render that is not ready yet
 * comes back without a result; the request is then repeated a few times.
 */
export async function fetchMeteogramUrl(name: string, location: GeoLocation, signal: AbortSignal): Promise<string> {
  const body = JSON.stringify({
    location: { type: 'latlon', lat: location.lat, lon: location.lon, station_name: '' },
    axis: {},
    epsgrams: name,
  })
  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    const response = await fetch(EPSGRAM_API, { method: 'POST', mode: 'cors', signal, body })
    if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`)
    const data = (await response.json()) as EpsgramResponse
    if (data.result) return data.result.url
    if (attempt < ATTEMPTS) await delay(RETRY_MS, signal)
  }
  throw new Error(`${name}: ECMWF hat kein Bild geliefert`)
}
