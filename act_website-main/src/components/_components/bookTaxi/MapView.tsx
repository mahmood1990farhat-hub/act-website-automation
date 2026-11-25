"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import { GoogleMap, Marker, Polyline } from "@react-google-maps/api";
import { decode } from "@googlemaps/polyline-codec";
import ProviderMap from "@/providers/ProviderMap";
import { bookingText } from "./booking-text";

type Props = {
  routePolyline?: string;
  /** Selected pickup, any stops, and drop-off, in travel order. */
  locations?: readonly google.maps.LatLngLiteral[];
};

const containerStyle = { width: "100%", height: "100%", borderRadius: "8px" };
const lineStyle = { strokeColor: "#317daf", strokeOpacity: 1, strokeWeight: 4, geodesic: true };

function MapView({ routePolyline, locations }: Props) {
  const { locale = "en" } = useParams<{ locale: string }>();
  const mapRef = useRef<google.maps.Map | null>(null);
  const path = useMemo(
    () => routePolyline ? decode(routePolyline, 5).map(([lat, lng]) => ({ lat, lng })) : [],
    [routePolyline]
  );
  const pins = useMemo(() => {
    if (locations?.length) return locations;
    return path.length > 1 ? [path[0], path[path.length - 1]] : path;
  }, [locations, path]);

  const fitMap = useCallback(() => {
    if (!mapRef.current) return;
    const bounds = new google.maps.LatLngBounds();
    pins.forEach(point => bounds.extend(point));
    path.forEach(point => bounds.extend(point));
    if (bounds.isEmpty()) return;
    if (bounds.getNorthEast().equals(bounds.getSouthWest())) {
      mapRef.current.setCenter(bounds.getCenter());
      mapRef.current.setZoom(15);
    } else {
      mapRef.current.fitBounds(bounds);
    }
  }, [pins, path]);

  useEffect(fitMap, [fitMap]);

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      onLoad={map => {
        mapRef.current = map;
        fitMap();
      }}
      onUnmount={() => { mapRef.current = null; }}
    >
      {path.length > 1 && <Polyline path={path} options={lineStyle} />}
      {pins.map((position, index) => {
        const pickup = index === 0;
        const endpoint = pickup || index === pins.length - 1;
        const label = endpoint
          ? bookingText(locale, pickup ? "Pickup" : "Drop-off")
          : String(index);
        return (
          <Marker
            key={index}
            position={position}
            title={label}
            icon={endpoint ? {
              url: pickup ? "/images/start-icon.svg" : "/images/end-icon.svg",
              scaledSize: new google.maps.Size(30, 30),
              anchor: new google.maps.Point(17, 17),
            } : undefined}
            label={{ text: label, color: "white", fontWeight: "bold", fontSize: endpoint ? "6px" : "12px" }}
          />
        );
      })}
    </GoogleMap>
  );
}

export default function GuardedMapView(props: Props) {
  return (
    <ProviderMap loadingHeight="h-full">
      <MapView {...props} />
    </ProviderMap>
  );
}
