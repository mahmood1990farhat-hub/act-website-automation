"use client"

import { useEffect, useState } from "react"

interface Location {
  lat: number
  lng: number
}

export function useTripTracking(tripId: string) {

  const [location, setLocation] = useState<Location | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {

    if (!tripId) return

    const socket = new WebSocket(
      `wss://act-backend.horizontechco.com/ws/trips/${tripId}/tracking/`
    )

    socket.onopen = () => {
      console.log("Tracking connected")
      setConnected(true)
    }

    socket.onmessage = (event) => {

      const data = JSON.parse(event.data)

      if (data.lat && data.lng) {

        setLocation({
          lat: data.lat,
          lng: data.lng
        })

      }

    }

    socket.onclose = () => {
      console.log("Tracking disconnected")
      setConnected(false)
    }

    return () => {
      socket.close()
    }

  }, [tripId])

  return {
    location,
    connected
  }
}