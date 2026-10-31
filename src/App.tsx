import MapViewer from './components/MapViewer'
import StartPage from './components/StartPage'
import { useHashRoute } from './hooks/useHashRoute'
import { useStoredLocation } from './hooks/useStoredLocation'

export default function App() {
  const [route, navigate] = useHashRoute()
  const [location, setLocation] = useStoredLocation()

  return route === 'maps'
    ? <MapViewer location={location} onBack={() => navigate('start')} />
    : <StartPage location={location} onLocationChange={setLocation} onOpenMaps={() => navigate('maps')} />
}
