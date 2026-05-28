// components/GoogleMapRoute.tsx

"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    google: any;
  }
}

export default function GoogleMapRoute({
  driverLoc,
  destLoc,
}: {
  driverLoc: { lat: number; lng: number };
  destLoc: { lat: number; lng: number };
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObj = useRef<any>(null);
  const directionsRenderer = useRef<any>(null);

  useEffect(() => {
    if (!window.google) {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY}`;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
      script.onload = initMap;
    } else initMap();

    function initMap() {
      mapObj.current = new window.google.maps.Map(mapRef.current, {
        center: driverLoc,
        zoom: 14,
      });
      directionsRenderer.current = new window.google.maps.DirectionsRenderer();
      directionsRenderer.current.setMap(mapObj.current);
      drawRoute();
    }

    function drawRoute() {
      new window.google.maps.DirectionsService().route(
        {
          origin: driverLoc,
          destination: destLoc,
          travelMode: window.google.maps.TravelMode.DRIVING,
        },
        (result: any, status: string) => {
          if (status === "OK") directionsRenderer.current.setDirections(result);
          else console.error("Directions request failed:", status);
        }
      );
    }
  }, [driverLoc, destLoc]);

  return <div ref={mapRef} className="w-full h-96 rounded-md" />;
}
