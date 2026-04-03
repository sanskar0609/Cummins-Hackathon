import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

export function useMapbox(containerRef, options = {}) {
  const mapRef = useRef(null)
  const [mapLoaded, setMapLoaded] = useState(false)

  const defaultOptions = {
    style: 'mapbox://styles/mapbox/dark-v11',
    center: [20, 20],
    zoom: 1.8,
    projection: 'globe',
    antialias: true,
    ...options
  }

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new mapboxgl.Map({
      container: containerRef.current,
      ...defaultOptions,
    })

    map.on('load', () => {
      // Add deep atmospheric fog for the globe projection
      map.setFog({
        color: 'rgb(4, 6, 12)',
        'high-color': 'rgb(6, 8, 20)',
        'horizon-blend': 0.08,
        'space-color': 'rgb(2, 3, 8)',
        'star-intensity': 0.6
      })

      // Subtle sea glow
      map.setPaintProperty('water', 'fill-color', '#040c18')

      setMapLoaded(true)
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      setMapLoaded(false)
    }
  }, [])

  return { map: mapRef.current, mapRef, mapLoaded }
}
