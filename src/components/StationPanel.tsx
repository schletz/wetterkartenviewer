import { useStoredStation } from '../hooks/useStoredStation'
import type { WeatherStation } from '../model/WeatherStation'
import StationPicker from './StationPicker'
import StationReadings from './StationReadings'

interface StationPanelProps {
  /** Asks to show the station viewer for a station. */
  onOpenStation: (station: WeatherStation) => void
}

/**
 * Live temperatures of a station in the header of the start page:
 * the picker while no station is stored, its readings afterwards.
 */
export default function StationPanel({ onOpenStation }: StationPanelProps) {
  const [station, setStation] = useStoredStation()
  return station
    ? <StationReadings station={station} onOpen={() => onOpenStation(station)} onClear={() => setStation(null)} />
    : <StationPicker onSelect={setStation} />
}
