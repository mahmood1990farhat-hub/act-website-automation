type QuoteRoutePoint = {
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
  return Number.isFinite(lat) && Number.isFinite(lng) && !(lat === 0 && lng === 0);
};

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
  const pickup = routePoints.find((point) => point.type === "pickup")?.point;
  const dropoff = routePoints.find((point) => point.type === "dropoff")?.point;
  if (!hasValidCoordinates(pickup) || !hasValidCoordinates(dropoff)) {
    throw new Error(locationValidationMessage);
  }

  const request: Record<string, unknown> = {
    pickup_location: pickup.coordinates,
    dropoff_location: dropoff.coordinates,
    trip_date: normalizeTripDate(formDetails.date),
    trip_time: formDetails.time,
    passengers_count: formDetails.numberOfPassengers,
    large_suitcase: formDetails.largeSuitcase,
    small_suitcase: formDetails.smallSuitcase,
    booking_details: {
      additional_requirements: { meet_and_greet: false },
    },
  };
  const stopPoints = routePoints
    .filter((point) => point.type === "stop")
    .map((point) => ({
      point_lat: point.point?.coordinates?.lat,
      point_lng: point.point?.coordinates?.lng,
    }));
  if (stopPoints.length) request.stop_points = stopPoints;
  return request;
}
