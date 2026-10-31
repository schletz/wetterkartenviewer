import { useEffect, useState } from 'react'
import { loadVideo } from '../services/videoLoader'

/** A downloaded video: the URL it was requested by and the object URL to play it from. */
export interface LoadedVideoSource {
  url: string
  objectUrl: string
}

export interface LoadedVideo {
  /** Last video that loaded, kept while the next one is still loading. */
  shown: LoadedVideoSource | null
  /** True when the requested video could not be loaded (e.g. HTTP 404). */
  failed: boolean
}

/**
 * Returns the video of ``url`` once it is downloaded and the previous one until then.
 * Switching the layer thus keeps the old chart on screen instead of an empty tile.
 */
export function useLoadedVideo(url: string | null): LoadedVideo {
  const [shown, setShown] = useState<LoadedVideoSource | null>(null)
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    if (url === null) return
    let current = true
    loadVideo(url).then((objectUrl) => {
      if (!current) return
      if (objectUrl) setShown({ url, objectUrl })
      else setFailed(url)
    })
    return () => {
      current = false
    }
  }, [url])

  return url === null ? { shown: null, failed: false } : { shown, failed: failed === url }
}
