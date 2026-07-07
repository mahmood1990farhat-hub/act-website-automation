export type AirportJourneyDirection = "arrival" | "departure" | "manual";

type RoutePointLike = {
  type?: string;
  point?: Record<string, unknown> | null;
};

const MINUTES_PER_DAY = 24 * 60;
const SUPPORTED_AIRPORT_PATTERNS = [
  /\bheathrow\b/i,
  /\bgatwick\b/i,
  /\bstansted\b/i,
  /\bluton\b/i,
  /\blondon city airport\b/i,
];

const getPointText = (point: Record<string, unknown>) =>
  [point.description, point.name_en, point.name_ar, point.formatted_address]
    .filter((value): value is string => typeof value === "string")
    .join(" ");

export const isSupportedAirportPoint = (
  point?: Record<string, unknown> | null
) => {
  if (!point) return false;

  const hasAirportIdentifier = [
    point.airport_id,
    point.airport_code,
    point.iata_code,
  ].some(
    (value) =>
      (typeof value === "number" && Number.isFinite(value)) ||
      (typeof value === "string" && value.trim().length > 0)
  );
  const hasAirportCategory = [point.type, point.category].some(
    (value) => typeof value === "string" && value.toLowerCase() === "airport"
  );
  const hasAirportPlaceType =
    Array.isArray(point.types) &&
    point.types.some(
      (value) => typeof value === "string" && value.toLowerCase() === "airport"
    );

  if (hasAirportIdentifier || hasAirportCategory || hasAirportPlaceType) return true;

  const pointText = getPointText(point);
  return SUPPORTED_AIRPORT_PATTERNS.some((pattern) => pattern.test(pointText));
};

export const getAirportJourneyDirection = (
  routePoints: RoutePointLike[]
): AirportJourneyDirection => {
  const pickup = routePoints.find((routePoint) => routePoint.type === "pickup");
  const dropoff = routePoints.find((routePoint) => routePoint.type === "dropoff");
  const pickupIsAirport = isSupportedAirportPoint(pickup?.point);
  const dropoffIsAirport = isSupportedAirportPoint(dropoff?.point);

  if (pickupIsAirport && !dropoffIsAirport) return "arrival";
  if (!pickupIsAirport && dropoffIsAirport) return "departure";

  return "manual";
};

export const parseTimeToMinutes = (time: string) => {
  const match = time.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return undefined;

  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return undefined;

  return hour * 60 + minute;
};

const normalizeMinutes = (minutes: number) =>
  ((minutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;

export const formatCustomerTime = (minutes: number) => {
  const normalized = normalizeMinutes(minutes);
  const hour24 = Math.floor(normalized / 60);
  const minute = normalized % 60;
  const hour12 = hour24 % 12 || 12;
  const period = hour24 >= 12 ? "PM" : "AM";

  return `${hour12}:${String(minute).padStart(2, "0")} ${period}`;
};

export const getDepartureGuidance = (pickupTime: string, flightTime: string) => {
  const pickupMinutes = parseTimeToMinutes(pickupTime);
  const flightMinutes = parseTimeToMinutes(flightTime);
  if (pickupMinutes === undefined || flightMinutes === undefined) return "";

  const minutesBeforeFlight = normalizeMinutes(flightMinutes - pickupMinutes);
  if (minutesBeforeFlight >= 120 && minutesBeforeFlight <= 180) return "";

  const windowStart = formatCustomerTime(flightMinutes - 180);
  const windowEnd = formatCustomerTime(flightMinutes - 120);

  return `For airport departures, we recommend choosing a pickup time around 2–3 hours before your flight departure. Your selected pickup time may be too close or too early. Suggested pickup time: between ${windowStart} and ${windowEnd}.`;
};

export const getArrivalGuidance = (pickupTime: string, landingTime: string) => {
  const pickupMinutes = parseTimeToMinutes(pickupTime);
  const landingMinutes = parseTimeToMinutes(landingTime);
  if (pickupMinutes === undefined || landingMinutes === undefined) return "";

  const minutesAfterLanding = normalizeMinutes(pickupMinutes - landingMinutes);
  const looksLikeExpectedArrivalPickup =
    minutesAfterLanding >= 60 && minutesAfterLanding <= 12 * 60;
  if (looksLikeExpectedArrivalPickup) return "";

  const suggestedPickup = formatCustomerTime(landingMinutes + 60);

  return `For airport arrivals, we recommend choosing a pickup time at least 1 hour after landing to allow time for immigration, baggage collection, and meeting your driver. Suggested pickup time: ${suggestedPickup} or later.`;
};
