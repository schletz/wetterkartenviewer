import { useState } from 'react'
import { isValidStation, type WeatherStation } from '../model/WeatherStation'

const STORAGE_KEY = 'wetterkartenviewer.station'

function load(): WeatherStation | null {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    return isValidStation(stored) ? stored : null
  } catch {
    return null
  }
}

/**
 * Station of the live temperatures, kept in localStorage independent of the location
 * (the nearest station may lie far higher than the place). Saving null removes the entry.
 */
export function useStoredStation(): [WeatherStation | null, (station: WeatherStation | null) => void] {
  const [station, setStation] = useState(load)

  const save = (next: WeatherStation | null) => {
    setStation(next)
    try {
      if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      else localStorage.removeItem(STORAGE_KEY)
    } catch {
      // Storage blocked (private window): the choice still holds for this visit.
    }
  }
  return [station, save]
}
