"use client";

import { useEffect, useState } from "react";

export default function GetMyLocation() {
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true; 

    const fetchLocation = () => {
      if (!navigator.geolocation) {
        if (isMounted) setError("المتصفح لا يدعم تحديد الموقع");
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (isMounted) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            setLocation({ lat, lng });}
        },
        (err) => {
          console.error("خطأ في جلب الموقع:", err);
          if (isMounted) setError("فشل في جلب الموقع");
        },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0,
        }
      );


      // setTimeout(fetchLocation, 1000);
    };

    fetchLocation();

    return () => {
      isMounted = false; 
    };
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-2">موقعي الحالي:</h1>
      {error && <p className="text-red-500">{error}</p>}
      {location ? (
        <p>
          Latitude: {location.lat} <br />
          Longitude: {location.lng}
        </p>
      ) : (
        <p>جارٍ جلب الموقع...</p>
      )}
    </div>
  );
}
