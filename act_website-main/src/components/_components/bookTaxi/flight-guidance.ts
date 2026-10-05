import { runtimeText } from "@/lib/customer-runtime";
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

export const formatCustomerTime = (minutes: number, locale = "en") => {
  const normalized = normalizeMinutes(minutes);
  const hour24 = Math.floor(normalized / 60);
  const minute = normalized % 60;
  if (locale !== "en" && locale !== "ar") return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }).format(new Date(Date.UTC(2020, 0, 1, hour24, minute)));
  const hour12 = hour24 % 12 || 12;
  const period = locale === "ar" ? (hour24 >= 12 ? "مساءً" : "صباحًا") : (hour24 >= 12 ? "PM" : "AM");

  return `${hour12}:${String(minute).padStart(2, "0")} ${period}`;
};

export const getDepartureGuidance = (pickupTime: string, flightTime: string, locale = "en") => {
  const pickupMinutes = parseTimeToMinutes(pickupTime);
  const flightMinutes = parseTimeToMinutes(flightTime);
  if (pickupMinutes === undefined || flightMinutes === undefined) return "";

  const minutesBeforeFlight = normalizeMinutes(flightMinutes - pickupMinutes);
  if (minutesBeforeFlight >= 120 && minutesBeforeFlight <= 180) return "";

  const windowStart = formatCustomerTime(flightMinutes - 180, locale);
  const windowEnd = formatCustomerTime(flightMinutes - 120, locale);

  return runtimeText(locale, "departureGuidance").replace("{windowStart}", windowStart).replace("{windowEnd}", windowEnd);
};

export const getArrivalGuidance = (pickupTime: string, landingTime: string, locale = "en") => {
  const pickupMinutes = parseTimeToMinutes(pickupTime);
  const landingMinutes = parseTimeToMinutes(landingTime);
  if (pickupMinutes === undefined || landingMinutes === undefined) return "";

  const minutesAfterLanding = normalizeMinutes(pickupMinutes - landingMinutes);
  const looksLikeExpectedArrivalPickup =
    minutesAfterLanding >= 60 && minutesAfterLanding <= 12 * 60;
  if (looksLikeExpectedArrivalPickup) return "";

  const suggestedPickup = formatCustomerTime(landingMinutes + 60, locale);

  return runtimeText(locale, "arrivalGuidance").replace("{suggestedPickup}", suggestedPickup);
};

