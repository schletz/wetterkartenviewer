import { useState } from 'react'
import { DEFAULT_LOCATION, isValidLocation, type GeoLocation } from '../model/GeoLocation'

const STORAGE_KEY = 'wetterkartenviewer.location'

function load(): GeoLocation {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as GeoLocation | null
    return stored && isValidLocation(stored) ? stored : DEFAULT_LOCATION
  } catch {
    return DEFAULT_LOCATION
  }
}

/** Location of the meteograms and the chart marker, kept in localStorage. */
export function useStoredLocation(): [GeoLocation, (location: GeoLocation) => void] {
  const [location, setLocation] = useState(load)

  const save = (next: GeoLocation) => {
    setLocation(next)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Storage blocked (private window): the location still holds for this visit.
    }
  }
  return [location, save]
}
