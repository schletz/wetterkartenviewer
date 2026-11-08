import { bandColour } from './colourBands'
import type { ColourBand } from './seriesFiles'

/** Colour classes of air temperatures in °C, shared by the value table, its legend and the station map. */
export const TEMPERATURE_BANDS: ColourBand[] = [
  [-Infinity, -10, '#4169e1'],
  [-10, 0, '#87cefa'],
  [0, 10, '#228b22'],
  [10, 20, '#7fff00'],
  [20, 30, '#ff8c00'],
  [30, Infinity, '#ff0000'],
]

/** Colour of a station or table cell without a value. */
export const NO_VALUE_COLOUR = '#ffffff'

/** Colour of a temperature; `NO_VALUE_COLOUR` for a missing value. */
export function temperatureColour(value: number | null): string {
  return value === null ? NO_VALUE_COLOUR : bandColour(TEMPERATURE_BANDS, value)
}

/** Legend text of a band, e.g. „< -10 °C“ or „0 bis 10 °C“. A band includes its lower limit. */
export function bandLabel([lower, upper]: ColourBand): string {
  if (lower === -Infinity) return `< ${upper} °C`
  if (upper === Infinity) return `≥ ${lower} °C`
  return `${lower} bis ${upper} °C`
}
