"use client";

import { useParams } from "next/navigation";
import { runtimeText } from "@/lib/customer-runtime";
import { useJsApiLoader } from "@react-google-maps/api";

export default function ProviderMap({ children }: { children: React.ReactNode }) {
  const { locale = "en" } = useParams<{locale: string}>();
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!,
    language: locale,
  });

  if (loadError) {
    return <div className="text-red-500 text-center">{runtimeText(locale, "mapUnavailable")}</div>;
  }

  if (!isLoaded) {
    return (
      <div className="flex justify-center bg-foreground items-center h-screen">
        <span className="sr-only">{runtimeText(locale, "loadingMap")}</span>
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  return <>{children}</>;
}
