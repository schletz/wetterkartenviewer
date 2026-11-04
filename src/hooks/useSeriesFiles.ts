import { useEffect, useState } from 'react'
import type { SeriesFiles } from '../model/seriesFiles'
import { fetchManifest, mapsUrl } from '../services/manifestLoader'

export type SeriesFilesState =
  | { status: 'loading' }
  /** The manifest lacks a required series (older pipeline): nothing to show. */
  | { status: 'missing' }
  | { status: 'error'; message: string }
  | { status: 'ready'; files: SeriesFiles }

/** Without these the diagram cannot be drawn. */
const REQUIRED = ['t850', 't2m', 'heights'] as const
/** Drawn when the manifest lists it. */
const OPTIONAL = ['thickness', 't500', 'rh850', 'rh700'] as const

/** Loads the temperature series files the manifest lists, once per page; their version keeps the browser cache apart. */
export function useSeriesFiles(): SeriesFilesState {
  const [state, setState] = useState<SeriesFilesState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    const load = async (): Promise<SeriesFilesState> => {
      const series = (await fetchManifest(controller.signal)).series ?? {}
      if (REQUIRED.some((name) => series[name] === undefined)) return { status: 'missing' }
      const names = [...REQUIRED, ...OPTIONAL.filter((name) => series[name] !== undefined)]
      const documents = await Promise.all(names.map(async (name) => {
        const { file, version } = series[name]
        const response = await fetch(mapsUrl(file, version), { signal: controller.signal })
        if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`)
        return [name, await response.json()] as const
      }))
      return { status: 'ready', files: Object.fromEntries(documents) as unknown as SeriesFiles }
    }
    load()
      .then(setState)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ status: 'error', message: String(error) })
      })
    return () => controller.abort()
  }, [])

  return state
}
