import type { MouseEvent } from 'react'
import type { TileConfig } from '../config/viewerConfig'
import type { ChartIndex } from '../model/ChartIndex'
import type { GeoLocation } from '../model/GeoLocation'
import ChartImage from './ChartImage'
import styles from './ChartTile.module.css'

interface ChartTileProps {
  index: ChartIndex
  tile: TileConfig
  layer: number
  step: number
  location: GeoLocation
  onNextLayer: () => void
  onEnlarge: () => void
}

/** One tile of the grid: left click shows the next layer, right click opens the large view. */
export default function ChartTile({ index, tile, layer, step, location, onNextLayer, onEnlarge }: ChartTileProps) {
  const enlarge = (event: MouseEvent) => {
    event.preventDefault()
    onEnlarge()
  }

  return (
    <div className={styles.tile} onClick={onNextLayer} onContextMenu={enlarge}>
      <ChartImage index={index} path={tile.layers[layer]} step={step} location={location} />
      {tile.layers.length > 1 && (
        <span className={styles.badge} title="Klick: nächster Layer">{layer + 1}/{tile.layers.length}</span>
      )}
    </div>
  )
}
