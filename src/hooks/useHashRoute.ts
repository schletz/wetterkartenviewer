import { useEffect, useState } from 'react'

export type Route = 'start' | 'maps'

function currentRoute(): Route {
  return window.location.hash === '#/maps' ? 'maps' : 'start'
}

/** Page selection in the URL hash, so the back button and bookmarks work without a router. */
export function useHashRoute(): [Route, (route: Route) => void] {
  const [route, setRoute] = useState(currentRoute)

  useEffect(() => {
    const onChange = () => setRoute(currentRoute())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const navigate = (next: Route) => {
    window.location.hash = next === 'maps' ? '#/maps' : ''
  }
  return [route, navigate]
}
