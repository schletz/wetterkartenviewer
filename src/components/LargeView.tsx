import { useRef, useState, type PointerEvent } from 'react'
import type { ChartPath } from '../config/viewerConfig'
import type { ChartIndex } from '../model/ChartIndex'
import { IMAGE_WIDTH } from '../model/ChartProjection'
import type { GeoLocation } from '../model/GeoLocation'
import ChartImage from './ChartImage'
import styles from './LargeView.module.css'

interface LargeViewProps {
  index: ChartIndex
  path: ChartPath
  step: number
  location: GeoLocation
  onNextLayer: () => void
  onClose: () => void
}

interface Drag {
  pointerX: number
  pointerY: number
  startX: number
  startY: number
}

/**
 * A chart at 1:1 pixel size in a window that can be dragged by its title bar.
 * There is no backdrop: the other tiles stay visible for comparison.
 */
export default function LargeView({ index, path, step, location, onNextLayer, onClose }: LargeViewProps) {
  const [position, setPosition] = useState(() => ({
    x: Math.max(0, (window.innerWidth - IMAGE_WIDTH) / 2),
    y: 60,
  }))
  const drag = useRef<Drag | null>(null)

  const startDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { pointerX: event.clientX, pointerY: event.clientY, startX: position.x, startY: position.y }
  }

  const moveDrag = (event: PointerEvent<HTMLDivElement>) => {
    const d = drag.current
    if (!d) return
    // Keep the title bar on screen, otherwise the window could not be grabbed again.
    setPosition({
      x: Math.min(Math.max(d.startX + event.clientX - d.pointerX, 100 - IMAGE_WIDTH), window.innerWidth - 100),
      y: Math.min(Math.max(d.startY + event.clientY - d.pointerY, 0), window.innerHeight - 30),
    })
  }

  const endDrag = () => {
    drag.current = null
  }

  return (
    <div className={styles.window} style={{ left: position.x, top: position.y }}>
      <div className={styles.titleBar} onPointerDown={startDrag} onPointerMove={moveDrag}
        onPointerUp={endDrag} onPointerCancel={endDrag}>
        <span>{path}</span>
        <button className={styles.close} onPointerDown={(e) => e.stopPropagation()} onClick={onClose}
          title="Schließen (Esc)">×</button>
      </div>
      <div onClick={onNextLayer}>
        <ChartImage index={index} path={path} step={step} location={location} className={styles.chart} />
      </div>
    </div>
  )
}
