import { useStoredStation } from '../hooks/useStoredStation'
import StationPicker from './StationPicker'
import StationReadings from './StationReadings'

/**
 * Live temperatures of a GeoSphere station in the header of the start page:
 * the picker while no station is stored, its readings afterwards.
 */
export default function StationPanel() {
  const [station, setStation] = useStoredStation()
  return station
    ? <StationReadings station={station} onClear={() => setStation(null)} />
    : <StationPicker onSelect={setStation} />
}
