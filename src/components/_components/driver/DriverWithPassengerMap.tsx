import { useEffect, useRef } from "react";

type LatLng = { lat: number; lng: number };

export default function LiveDriverRouteWithWaypoints({
  passengerLocation,
  waypoints = [],
  extraMarkers = [],
}: {
  passengerLocation: LatLng;
  waypoints?: LatLng[];
  extraMarkers?: {
    position: LatLng;
    label?: string;
    title?: string;
    color?: string;
  }[];
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const driverMarker = useRef<any>(null);
  const passengerMarker = useRef<any>(null);
  const stopMarkers = useRef<any[]>([]);
  const directionsService = useRef<any>(null);
  const directionsRenderer = useRef<any>(null);
  const otherMarkers = useRef<any[]>([]);

  const initMap = (driverPos: LatLng) => {
    map.current = new google.maps.Map(mapRef.current!, {
      center: driverPos,
      zoom: 14,
    });

    driverMarker.current = new google.maps.Marker({
      position: driverPos,
      map: map.current,
      label: "🚗",
      title: "موقع السائق",
    });

    // 🧍 الراكب
    passengerMarker.current = new google.maps.Marker({
      position: passengerLocation,
      map: map.current,
      label: "🧍",
      title: "موقع الراكب",
    });

    // 🔴 نقاط التوقف
    waypoints.forEach((point, index) => {
      const marker = new google.maps.Marker({
        position: point,
        map: map.current,
        // label: `${index + 1}`,
        title: `نقطة توقف ${index + 1}`,
        label: {
          text: `${index + 1} stop`,
          color: "black",
          fontWeight: "bold",
        },
        icon: {
          path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
          fillColor: "#f00",
          fillOpacity: 1,

          strokeWeight: 1,
          scale: 5,
        },
      });
      stopMarkers.current.push(marker);
    });

    // 📍 علامات إضافية
    extraMarkers.forEach((markerData) => {
      const marker = new google.maps.Marker({
        position: markerData.position,
        map: map.current,
        title: markerData.title || "نقطة",
        label: markerData.label,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 6,
          fillColor: markerData.color || "#000",
          fillOpacity: 1,
          strokeWeight: 1,
        },
      });
      otherMarkers.current.push(marker);
    });

    directionsService.current = new google.maps.DirectionsService();
    directionsRenderer.current = new google.maps.DirectionsRenderer({
      map: map.current,
      suppressMarkers: true,
      polylineOptions: {
        strokeColor: "#007bff",
        strokeWeight: 5,
      },
    });

    drawRoute(driverPos);
  };

  const drawRoute = (driverPos: LatLng) => {
    if (!directionsService.current || !directionsRenderer.current) return;

    directionsService.current.route(
      {
        origin: driverPos,
        destination: passengerLocation,
        waypoints: waypoints.map((point) => ({
          location: point,
          stopover: true,
        })),
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result: any, status: any) => {
        if (status === "OK") {
          directionsRenderer.current.setDirections(result);
        } else {
          console.error("تعذر رسم المسار:", status);
        }
      }
    );
  };

  useEffect(() => {
    const trackDriver = () => {
      const watcher = navigator.geolocation.watchPosition(
        (position) => {
          const driverPos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };

          if (!map.current) {
            initMap(driverPos);
          } else {
            driverMarker.current.setPosition(driverPos);
            drawRoute(driverPos);
          }
        },
        (err) => {
          console.error("خطأ بتحديد الموقع:", err);
        },
        { enableHighAccuracy: true }
      );

      return () => navigator.geolocation.clearWatch(watcher);
    };

    if (!window.google) {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY}`;
      script.async = true;
      script.defer = true;
      script.onload = trackDriver;
      document.head.appendChild(script);
    } else {
      trackDriver();
    }
  }, [passengerLocation, waypoints, extraMarkers]);


  console.log();
  
  return (
    <div ref={mapRef} className="w-full h-[500px] rounded shadow border" />
  );
}
