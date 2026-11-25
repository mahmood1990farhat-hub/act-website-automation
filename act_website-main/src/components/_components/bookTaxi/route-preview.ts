import type { QueryClient } from "@tanstack/react-query";

type RoutePreview = { route_polyline: string; route_proof: string };

async function fetchPreview(body: string, signal: AbortSignal): Promise<RoutePreview> {
  const request = new AbortController();
  const abort = () => request.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) abort();
  const timeout = setTimeout(abort, 6000);
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/api/trips/route-preview/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: request.signal,
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Route preview unavailable");
    const preview = await response.json();
    if (typeof preview?.route_polyline !== "string" || !preview.route_polyline ||
        typeof preview.route_proof !== "string" || !preview.route_proof) {
      throw new Error("Incomplete route preview");
    }
    return preview;
  } finally {
    clearTimeout(timeout);
    signal.removeEventListener("abort", abort);
  }
}

export function routePreviewQuery(requestKey: string | null) {
  return {
    queryKey: ["booking-route-preview", requestKey] as const,
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchPreview(requestKey!, signal),
    staleTime: 60_000,
    gcTime: 60_000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    networkMode: "always" as const,
  };
}

export async function getQuoteProof(client: QueryClient, requestKey: string | null) {
  if (!requestKey) return;
  const options = routePreviewQuery(requestKey);
  const cached = client.getQueryData<RoutePreview>(options.queryKey);
  if (cached) return cached.route_proof;
  // Join the pending preview for these coordinates. A failed preview never blocks a quote.
  if (client.getQueryState(options.queryKey)?.fetchStatus === "fetching") {
    try { return (await client.fetchQuery(options)).route_proof; }
    catch { return undefined; }
  }
}
