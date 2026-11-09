import { bandLabel, NO_VALUE_COLOUR, TEMPERATURE_BANDS } from '../model/temperatureBands'
import { STATION_SOURCES } from '../services/stationSources'
import styles from './StationLegend.module.css'

/** The map shows the stations of every network, so each of them is cited. */
const ATTRIBUTIONS = Object.values(STATION_SOURCES).map((source) => source.attribution).join('; ')

/** One colour swatch with its text. */
function Entry({ colour, text }: { colour: string, text: string }) {
  return (
    <li className={styles.entry}>
      <span className={styles.swatch} style={{ background: colour }} />
      {text}
    </li>
  )
}

/** Meaning of the colours of the value table and the station map. */
export default function StationLegend() {
  return (
    <div className={styles.legend}>
      <ul className={styles.list}>
        {TEMPERATURE_BANDS.map((band) => <Entry key={band[2]} colour={band[2]} text={bandLabel(band)} />)}
        <Entry colour={NO_VALUE_COLOUR} text="nicht verfügbar" />
      </ul>
      <div className={styles.note}>ungeprüfte Rohdaten, Quelle: {ATTRIBUTIONS}</div>
    </div>
  )
}
