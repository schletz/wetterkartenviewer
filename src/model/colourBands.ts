import type { ColourBand } from './seriesFiles'

/** Colour of the band a value falls in; values outside the bands get the nearest band, as on the charts. */
export function bandColour(bands: ColourBand[], value: number): string {
  const band = bands.find(([, upper]) => value < upper) ?? bands[bands.length - 1]
  return band[2]
}
