import { useEffect, useState } from 'react'
import { viewerConfig } from '../config/viewerConfig'
import type { ChartIndex } from '../model/ChartIndex'
import type { GeoLocation } from '../model/GeoLocation'
import ChartTile from './ChartTile'
import LargeView from './LargeView'
import StepSlider, { MAX_STEP } from './StepSlider'
import styles from './ChartGrid.module.css'

interface ChartGridProps {
  index: ChartIndex
  location: GeoLocation
  onBack: () => void
}

/** Forecast hour closest to now (rounded down), so the grid opens at the present. */
function currentStep(index: ChartIndex): number {
  const hours = Math.floor((Date.now() - index.runTime.getTime()) / 3_600_000)
  return Math.min(Math.max(hours, 0), MAX_STEP)
}

/** Slider, tiles and the large view of one run. */
export default function ChartGrid({ index, location, onBack }: ChartGridProps) {
  const tiles = viewerConfig.tiles
  const [step, setStep] = useState(() => currentStep(index))
  const [layers, setLayers] = useState(() => tiles.map(() => 0))
  const [enlarged, setEnlarged] = useState<number | null>(null)

  const nextLayer = (tile: number) =>
    setLayers((current) => current.map((layer, i) => (i === tile ? (layer + 1) % tiles[tile].layers.length : layer)))

  // Arrow keys jump to the previous/next step that has a chart in any visible layer;
  // on the focused slider they keep their native 1 h steps.
  useEffect(() => {
    const visible = tiles.map((tile, i) => tile.layers[layers[i]])
    const steps = index.steps(visible)
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setEnlarged(null)
      if (event.target instanceof HTMLInputElement) return
      if (event.key === 'ArrowRight') {
        setStep((s) => steps.find((candidate) => candidate > s) ?? s)
      } else if (event.key === 'ArrowLeft') {
        setStep((s) => steps.findLast((candidate) => candidate < s) ?? s)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, tiles, layers])

  return (
    <main className={styles.viewer}>
      <header className={styles.toolbar}>
        <button onClick={onBack}>Start</button>
        <StepSlider step={step} runTime={index.runTime} onChange={setStep} />
      </header>
      <section className={styles.grid}>
        {tiles.map((tile, i) => (
          <ChartTile key={i} index={index} tile={tile} layer={layers[i]} step={step} location={location}
            onNextLayer={() => nextLayer(i)} onEnlarge={() => setEnlarged(i)} />
        ))}
      </section>
      {enlarged !== null && (
        <LargeView index={index} path={index.resolve(tiles[enlarged].layers[layers[enlarged]], step)} step={step}
          location={location}
          onNextLayer={() => nextLayer(enlarged)} onClose={() => setEnlarged(null)} />
      )}
    </main>
  )
}
