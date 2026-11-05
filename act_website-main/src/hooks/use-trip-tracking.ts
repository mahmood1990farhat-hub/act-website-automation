"use client"

import { useEffect, useState } from "react"
import { buildTripTrackingUrl } from "@/lib/trip-tracking-url"

interface Location {
  lat: number
  lng: number
}

export function useTripTracking(tripId: string) {

  const [location, setLocation] = useState<Location | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    setLocation(null)
    setConnected(false)
    const url = buildTripTrackingUrl(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      tripId
    )
    if (!url) return
    const socket = new WebSocket(url)
    let disposed = false

    socket.onopen = () => {
      if (disposed) return
      console.log("Tracking connected")
      setConnected(true)
    }

    socket.onmessage = (event) => {
      if (disposed) return

      const data = JSON.parse(event.data)

      if (data.lat && data.lng) {

        setLocation({
          lat: data.lat,
          lng: data.lng
        })

      }

    }

    socket.onclose = () => {
      if (disposed) return
      console.log("Tracking disconnected")
      setConnected(false)
    }

    return () => {
      disposed = true
      socket.onopen = null
      socket.onmessage = null
      socket.onclose = null
      socket.close()
    }

  }, [tripId])

  return {
    location,
    connected
  }
}
