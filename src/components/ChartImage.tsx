import { useEffect, useRef, useState } from 'react'
import type { ChartPath } from '../config/viewerConfig'
import type { ChartFrame, ChartIndex } from '../model/ChartIndex'
import { IMAGE_HEIGHT, IMAGE_WIDTH, projectionOf } from '../model/ChartProjection'
import type { GeoLocation } from '../model/GeoLocation'
import { useLoadedVideo } from '../hooks/useLoadedVideo'
import styles from './ChartImage.module.css'

interface ChartImageProps {
  index: ChartIndex
  path: ChartPath
  step: number
  location: GeoLocation
  className?: string
}

/** Text of the placeholder, or null when the chart can be shown. */
function placeholderText(index: ChartIndex, path: ChartPath, frame: ChartFrame | null, failed: boolean): string | null {
  if (frame) return failed ? `${path} konnte nicht geladen werden` : null
  const first = index.firstStep(path)
  return first === null ? 'keine Karten in diesem Lauf' : `ab +${first} h`
}

/**
 * The latest chart of a product at or before ``step`` with the location marked: a frame of
 * the product's video, or a placeholder of the same size if the product starts later or its
 * video fails to load.
 */
export default function ChartImage({ index, path, step, location, className = '' }: ChartImageProps) {
  const frame = index.frame(path, step)
  const url = index.videoUrl(path)
  const { shown, failed } = useLoadedVideo(url)
  // A browser without AV1 support downloads the video but cannot decode it.
  const [undecodable, setUndecodable] = useState<string | null>(null)
  const video = useRef<HTMLVideoElement>(null)
  const pixel = projectionOf(path)?.toPixel(location) ?? null
  // Seek only in the video of this path; while another layer's video is still shown, its frame stays.
  const time = frame && shown?.url === url ? index.frameTime(frame) : null

  useEffect(() => {
    const element = video.current
    // Before its metadata the element cannot seek; onLoadedMetadata catches up.
    if (element && time !== null && element.readyState >= HTMLMediaElement.HAVE_METADATA) element.currentTime = time
  }, [time])

  const message = placeholderText(index, path, frame, failed || (url !== null && undecodable === url))
  if (message !== null) {
    return (
      <div className={`${styles.chart} ${styles.placeholder} ${className}`}>
        <span>{path}</span>
        <span>{message}</span>
      </div>
    )
  }

  return (
    <div className={`${styles.chart} ${className}`}>
      {shown && (
        <video ref={video} className={styles.image} src={shown.objectUrl} muted playsInline preload="auto"
          onLoadedMetadata={(event) => {
            if (time !== null) event.currentTarget.currentTime = time
          }}
          onError={() => setUndecodable(shown.url)} />
      )}
      {pixel && (
        <span className={styles.marker}
          style={{ left: `${(pixel.x / IMAGE_WIDTH) * 100}%`, top: `${(pixel.y / IMAGE_HEIGHT) * 100}%` }} />
      )}
    </div>
  )
}
