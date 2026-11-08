import { useId, useState, type FormEvent } from 'react'
import { useStationList } from '../hooks/useStationList'
import { stationLabel, type WeatherStation } from '../model/WeatherStation'
import styles from './StationPicker.module.css'

interface StationPickerProps {
  onSelect: (station: WeatherStation) => void
}

/**
 * The station whose label equals the text, else the only one (or, on Enter, the first one) whose label contains it.
 * Case is ignored, so „gumpold“ and Enter is enough.
 */
function matchStation(stations: WeatherStation[], text: string, takeFirst: boolean): WeatherStation | undefined {
  const query = text.trim().toLocaleLowerCase('de')
  if (!query) return undefined
  const exact = stations.find((station) => stationLabel(station).toLocaleLowerCase('de') === query)
  if (exact) return exact
  const candidates = stations.filter((station) => stationLabel(station).toLocaleLowerCase('de').includes(query))
  return candidates.length === 1 || (takeFirst && candidates.length > 0) ? candidates[0] : undefined
}

/**
 * Text field with autocompletion (native datalist) over the active TAWES stations, loaded once on mount.
 * Choosing a suggestion selects the station at once; Enter takes the first station that contains the text.
 */
export default function StationPicker({ onSelect }: StationPickerProps) {
  const listId = useId()
  const list = useStationList()
  const [text, setText] = useState('')
  const stations = list && 'stations' in list ? list.stations : []

  const change = (value: string) => {
    setText(value)
    // A picked suggestion arrives as its full label; typing a full label selects as well.
    const exact = stations.find((station) => stationLabel(station) === value)
    if (exact) onSelect(exact)
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const station = matchStation(stations, text, true)
    if (station) onSelect(station)
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <label className={styles.label}>
        Station:
        <input className={styles.input} type="search" list={listId} value={text}
          placeholder={list === null ? 'Stationen werden geladen …' : 'z. B. Gumpoldskirchen'}
          disabled={list === null || 'error' in list}
          onChange={(e) => change(e.target.value)} />
      </label>
      <datalist id={listId}>
        {stations.map((station) => (
          <option key={station.id} value={stationLabel(station)}>{station.state}</option>
        ))}
      </datalist>
      {list && 'error' in list && <span className={styles.error}>{list.error}</span>}
    </form>
  )
}
