import { useEffect, type RefObject } from 'react'

/** Width of the edge zones in px, at most this share of the element width. */
const EDGE_ZONE = 140
const EDGE_ZONE_SHARE = 0.15
/** Speed at the outermost point of a zone in px/s; it grows with the square of the depth into the zone. */
const MAX_SPEED = 1600

/**
 * Scrolls a horizontally overflowing element while the mouse rests near its left or right edge,
 * faster the closer to the edge; a vertical wheel turn scrolls it horizontally.
 * The zones reach beyond the element up to the window border, so a mouse pushed against the screen edge keeps scrolling.
 * Touch and pen keep the native scrolling; nothing happens while the element does not overflow.
 */
export function useEdgeScroll(ref: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const element = ref.current
    if (element === null) return
    const overflows = () => element.scrollWidth > element.clientWidth

    let speed = 0
    let frame = 0
    let lastTime = 0
    // scrollLeft may be rounded to whole pixels, so the exact position is kept here.
    let position = 0

    const tick = (time: number) => {
      const dt = Math.min(time - lastTime, 50) / 1000
      lastTime = time
      // Resynchronise when something else (scrollbar, wheel, keyboard) moved the element.
      if (Math.abs(element.scrollLeft - position) > 1) position = element.scrollLeft
      const max = element.scrollWidth - element.clientWidth
      position = Math.max(0, Math.min(max, position + speed * dt))
      element.scrollLeft = position
      const atEnd = (speed < 0 && position <= 0) || (speed > 0 && position >= max)
      frame = speed === 0 || atEnd ? 0 : requestAnimationFrame(tick)
    }

    const setSpeed = (value: number) => {
      speed = value
      if (speed !== 0 && frame === 0) {
        position = element.scrollLeft
        lastTime = performance.now()
        frame = requestAnimationFrame(tick)
      }
    }

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse' || !overflows()) return setSpeed(0)
      const rect = element.getBoundingClientRect()
      if (event.clientY < rect.top || event.clientY > rect.bottom) return setSpeed(0)
      const zone = Math.min(EDGE_ZONE, rect.width * EDGE_ZONE_SHARE)
      const left = (rect.left + zone - event.clientX) / zone
      const right = (event.clientX - (rect.right - zone)) / zone
      const depth = Math.min(1, Math.max(left, right, 0))
      setSpeed((left > 0 ? -1 : 1) * MAX_SPEED * depth * depth)
    }

    // Leaving the window: relatedTarget is null.
    const onMouseOut = (event: MouseEvent) => {
      if (event.relatedTarget === null) setSpeed(0)
    }
    const stop = () => setSpeed(0)

    const onWheel = (event: WheelEvent) => {
      if (!overflows() || event.ctrlKey || Math.abs(event.deltaX) >= Math.abs(event.deltaY)) return
      event.preventDefault()
      // deltaMode 1 counts lines (Firefox), not pixels.
      element.scrollLeft += event.deltaMode === 1 ? event.deltaY * 40 : event.deltaY
    }

    document.addEventListener('pointermove', onPointerMove)
    document.addEventListener('mouseout', onMouseOut)
    window.addEventListener('blur', stop)
    element.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('pointermove', onPointerMove)
      document.removeEventListener('mouseout', onMouseOut)
      window.removeEventListener('blur', stop)
      element.removeEventListener('wheel', onWheel)
    }
  }, [ref])
}
