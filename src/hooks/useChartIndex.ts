import { useEffect, useState } from 'react'
import { ChartIndex, type Manifest } from '../model/ChartIndex'

export type ChartIndexState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; index: ChartIndex }

/** Loads maps/manifest.json once; no-cache, because every run replaces it under the same name. */
export function useChartIndex(): ChartIndexState {
  const [state, setState] = useState<ChartIndexState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${import.meta.env.BASE_URL}maps/manifest.json`, { cache: 'no-cache', signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`manifest.json: HTTP ${response.status}`)
        return response.json() as Promise<Manifest>
      })
      .then((manifest) => setState({ status: 'ready', index: new ChartIndex(manifest) }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ status: 'error', message: String(error) })
      })
    return () => controller.abort()
  }, [])

  return state
}
