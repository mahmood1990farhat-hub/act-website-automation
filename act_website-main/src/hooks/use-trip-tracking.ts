"use client"

import { useEffect, useState } from "react"
import { buildTripTrackingUrl } from "@/lib/trip-tracking-url"

interface Location {
  lat: number
  lng: number
  heading: number | null
}

export type TrackingStatus =
  | "connecting" | "waiting" | "live" | "stale"
  | "unauthorized" | "ended" | "completed" | "cancelled" | "disconnected" | "unavailable"

export function trackingStatusText(status: TrackingStatus, locale = "en") {
  const text = {
    connecting: ["Connecting to trip tracking…", "جارٍ الاتصال بتتبع الرحلة…"],
    waiting: ["Waiting for a fresh driver location…", "في انتظار موقع حديث للسائق…"],
    live: ["Live driver location", "موقع السائق المباشر"],
    stale: ["Driver location is out of date. Waiting for an update…", "موقع السائق قديم. في انتظار تحديث…"],
    unauthorized: ["Tracking access was not authorised. Sign in again to the account for this trip.", "لم يُصرّح بالوصول إلى التتبع. سجّل الدخول مجددًا بالحساب المرتبط بهذه الرحلة."],
    ended: ["Trip tracking has ended.", "انتهى تتبع الرحلة."],
    completed: ["Trip completed. Tracking has stopped.", "اكتملت الرحلة. توقف التتبع."],
    cancelled: ["Trip cancelled. Tracking has stopped.", "أُلغيت الرحلة. توقف التتبع."],
    disconnected: ["Tracking disconnected. Reopen the trip to reconnect.", "انقطع اتصال التتبع. أعد فتح الرحلة للاتصال مجددًا."],
    unavailable: ["Trip tracking is unavailable.", "تتبع الرحلة غير متاح."],
  }
  return text[status][locale === "ar" ? 1 : 0]
}

const MAX_LOCATION_AGE_MS = 30_000
const MAX_CLOCK_SKEW_MS = 5_000

export function useTripTracking(tripId: string, token?: string) {
  const [location, setLocation] = useState<Location | null>(null)
  const [connected, setConnected] = useState(false)
  const [status, setStatus] = useState<TrackingStatus>("connecting")

  useEffect(() => {
    setLocation(null)
    setConnected(false)
    setStatus(token ? "connecting" : "unauthorized")
    if (!token) return

    const url = buildTripTrackingUrl(process.env.NEXT_PUBLIC_API_BASE_URL, tripId)
    if (!url) {
      setStatus("unavailable")
      return
    }

    let socket: WebSocket
    try {
      socket = new WebSocket(url)
    } catch {
      setStatus("unavailable")
      return
    }
    let disposed = false
    let authenticated = false
    let stopped = false
    let freshnessTimer: ReturnType<typeof setTimeout> | undefined
    let authenticationTimer: ReturnType<typeof setTimeout> | undefined

    const clearLocation = () => {
      clearTimeout(freshnessTimer)
      freshnessTimer = undefined
      setLocation(null)
    }
    const stop = (nextStatus: TrackingStatus) => {
      authenticated = false
      stopped = true
      clearTimeout(authenticationTimer)
      clearLocation()
      setConnected(false)
      setStatus(nextStatus)
    }

    socket.onopen = () => {
      if (disposed || stopped) return
      // Send credentials only in the socket message, never its URL.
      try {
        socket.send(JSON.stringify({ type: "viewer_auth", access: token }))
      } catch {
        stop("disconnected")
        socket.close()
      }
    }

    socket.onmessage = (event) => {
      if (disposed || stopped) return
      try {
        const data = JSON.parse(event.data)
        if (!data || typeof data !== "object") return
        if (data.type === "auth_error") {
          stop("unauthorized")
          socket.close()
          return
        }
        if (data.type === "auth_ok" && data.role === "viewer") {
          if (authenticated) return
          authenticated = true
          clearTimeout(authenticationTimer)
          setConnected(true)
          setStatus("waiting")
          return
        }
        if (!authenticated) return
        if (data.type === "ended") {
          stop(data.reason === "completed" || data.reason === "cancelled" ? data.reason : "ended")
          socket.close()
          return
        }
        if (data.type !== "location" || !data.location) return

        const { lat, lng, heading, received_at } = data.location
        if (
          typeof lat !== "number" || !Number.isFinite(lat) || Math.abs(lat) > 90 ||
          typeof lng !== "number" || !Number.isFinite(lng) || Math.abs(lng) > 180 ||
          typeof received_at !== "string"
        ) return

        // received_at is the server receipt time, not proof of a fresh GPS fix.
        // The driver separately rejects stale GPS measurements before publishing.
        const age = Date.now() - Date.parse(received_at)
        if (!Number.isFinite(age) || age < -MAX_CLOCK_SKEW_MS || age >= MAX_LOCATION_AGE_MS) return

        clearTimeout(freshnessTimer)
        setLocation({
          lat,
          lng,
          heading: typeof heading === "number" && Number.isFinite(heading) ? heading : null,
        })
        setStatus("live")
        freshnessTimer = setTimeout(() => {
          if (disposed || stopped) return
          clearLocation()
          setStatus("stale")
        }, MAX_LOCATION_AGE_MS - Math.max(0, age))
      } catch {
        // Malformed frames do not update the marker or extend its freshness.
      }
    }

    socket.onclose = () => {
      if (!disposed && !stopped) stop("disconnected")
    }
    socket.onerror = () => {
      if (disposed || stopped) return
      stop("disconnected")
      socket.close()
    }
    authenticationTimer = setTimeout(() => {
      if (disposed || stopped || authenticated) return
      stop("unavailable")
      socket.close()
    }, 15_000)

    return () => {
      disposed = true
      authenticated = false
      clearTimeout(authenticationTimer)
      clearTimeout(freshnessTimer)
      socket.onopen = null
      socket.onmessage = null
      socket.onclose = null
      socket.onerror = null
      socket.close()
    }
  }, [tripId, token])

  return { location, connected, status }
}
