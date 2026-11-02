import { useEffect, useState } from 'react'
import { ChartIndex } from '../model/ChartIndex'
import { fetchManifest } from '../services/manifestLoader'

export type ChartIndexState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; index: ChartIndex }

/** Loads maps/manifest.json once. */
export function useChartIndex(): ChartIndexState {
  const [state, setState] = useState<ChartIndexState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchManifest(controller.signal)
      .then((manifest) => setState({ status: 'ready', index: new ChartIndex(manifest) }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ status: 'error', message: String(error) })
      })
    return () => controller.abort()
  }, [])

  return state
}
