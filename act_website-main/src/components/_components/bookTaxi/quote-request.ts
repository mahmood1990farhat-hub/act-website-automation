export type QuoteRoutePoint = {
  type: "pickup" | "stop" | "dropoff";
  point: any | null;
};

type QuoteFormDetails = {
  date: string;
  time: string;
  numberOfPassengers: number;
  largeSuitcase: number;
  smallSuitcase: number;
};

export const locationValidationMessage =
  "Please select pickup and drop-off from the address suggestions and wait for them to load.";

export const hasValidCoordinates = (point: any) => {
  const lat = point?.coordinates?.lat;
  const lng = point?.coordinates?.lng;
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 && lat <= 90 &&
    lng >= -180 && lng <= 180 &&
    !(lat === 0 && lng === 0)
  );
};

type Coordinate = { lat: number; lng: number };

export const isSelectedRoutePoint = ({ point }: QuoteRoutePoint) =>
  Boolean(point?.id || point?.place_id) && hasValidCoordinates(point);

function routeRequest(locations: Coordinate[]) {
  const stops = locations.slice(1, -1);
  return {
    pickup_location: locations[0],
    dropoff_location: locations[locations.length - 1],
    ...(stops.length > 0 && {
      stop_points: stops.map(({ lat, lng }) => ({ point_lat: lat, point_lng: lng })),
    }),
  };
}

function orderedRoutePoints(points: QuoteRoutePoint[]) {
  return [
    points.find(p => p.type === "pickup"),
    ...points.filter(p => p.type === "stop"),
    points.find(p => p.type === "dropoff"),
  ];
}

export function selectedPreviewRoute(points: QuoteRoutePoint[]) {
  const ordered = orderedRoutePoints(points);
  const located = ordered.filter(p => p && isSelectedRoutePoint(p));
  const endpointsReady = [ordered[0], ordered[ordered.length - 1]].every(p => p && isSelectedRoutePoint(p));
  const locations: Coordinate[] = endpointsReady
    ? located.map(p => ({ lat: p!.point.coordinates.lat, lng: p!.point.coordinates.lng }))
    : [];
  return {
    locations,
    // A blank or unresolved stop invalidates the old road line, but keep the selected pins.
    requestKey: locations.length === ordered.length ? JSON.stringify(routeRequest(locations)) : null,
  };
}

const isNonNegativeInteger = (value: number) => Number.isInteger(value) && value >= 0;

export const hasValidQuoteCounts = (formDetails: QuoteFormDetails) =>
  Number.isInteger(formDetails.numberOfPassengers) &&
  formDetails.numberOfPassengers >= 1 &&
  formDetails.numberOfPassengers <= 7 &&
  isNonNegativeInteger(formDetails.largeSuitcase) &&
  isNonNegativeInteger(formDetails.smallSuitcase) &&
  formDetails.largeSuitcase + formDetails.smallSuitcase <= 8;

const normalizeTripDate = (date: string) => {
  const [year, month, day] = date.split("-");
  if (!year || !month || !day) return date;
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
};

export function buildTripQuoteRequest({
  routePoints,
  formDetails,
}: {
  routePoints: QuoteRoutePoint[];
  formDetails: QuoteFormDetails;
}) {
  const ordered = orderedRoutePoints(routePoints);
  if (ordered.some(p => !hasValidCoordinates(p?.point))) {
    throw new Error(locationValidationMessage);
  }
  if (!hasValidQuoteCounts(formDetails)) {
    throw new Error("Please check the passenger and luggage counts before requesting a price.");
  }

  const request: Record<string, unknown> = {
    ...routeRequest(ordered.map(p => p!.point.coordinates)),
    trip_date: normalizeTripDate(formDetails.date),
    trip_time: formDetails.time,
    passengers_count: formDetails.numberOfPassengers,
    large_suitcase: formDetails.largeSuitcase,
    small_suitcase: formDetails.smallSuitcase,
    booking_details: {
      additional_requirements: { meet_and_greet: false },
    },
  };
  return request;
}
