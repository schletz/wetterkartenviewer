const loaded = new Map<string, Promise<string | null>>()

/** Whether a response holds a video; the Vite dev server answers a missing file with index.html and HTTP 200. */
function isVideo(response: Response): boolean {
  return response.ok && (response.headers.get('content-type') ?? '').startsWith('video/')
}

/**
 * Downloads a video once and returns an object URL of it, or null on errors (e.g. HTTP 404)
 * instead of rejecting, so the caller decides whether to report it. Holding the whole file
 * lets every seek of the slider decode locally instead of waiting for range requests.
 */
export function loadVideo(url: string): Promise<string | null> {
  let video = loaded.get(url)
  if (!video) {
    video = fetch(url)
      .then((response) => (isVideo(response) ? response.blob() : null))
      .then((blob) => (blob ? URL.createObjectURL(blob) : null))
      .catch(() => null)
    loaded.set(url, video)
  }
  return video
}
