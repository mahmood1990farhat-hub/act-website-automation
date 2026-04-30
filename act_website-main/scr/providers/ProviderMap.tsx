"use client";

import { useJsApiLoader } from "@react-google-maps/api";

export default function ProviderMap({ children }: { children: React.ReactNode }) {
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!,
  });

  if (loadError) {
    return <div className="text-red-500 text-center">فشل تحميل خرائط Google</div>;
  }

  if (!isLoaded) {
    return (
      <div className="flex justify-center bg-foreground items-center h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  return <>{children}</>;
}
