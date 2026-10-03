import type { RoutePoint, PassengerDetailsForm, ChildInfantTravelForm, FlightDetailsForm, AdditionalRequirementsForm } from "@/components/_components/bookTaxi";
export const LANGUAGE_CHANGE_EVENT = "act:before-language-change";
const KEY = "act:language-transfer:v1";
const TTL = 5 * 60 * 1000;
export type BookingDraft = {
  routePoints: RoutePoint[];
  formDetails: { date: string; time: string; smallSuitcase: number; largeSuitcase: number; adults: number; children: number; infants: number; numberOfPassengers: number };
  passengerDetails: PassengerDetailsForm;
  childInfantTravel: ChildInfantTravelForm;
  flightDetails: FlightDetailsForm;
  additionalRequirements: AdditionalRequirementsForm;
};
function fields(value: any, strings: string[], numbers: string[] = []): any {
  if (!value || typeof value !== "object") throw Error("Invalid booking draft");
  const out: Record<string, string | number> = {};
  for (const key of strings) {
    if (typeof value[key] !== "string" || value[key].length > 5000) throw Error("Invalid draft field");
    out[key] = value[key];
  }
  for (const key of numbers) {
    if (!Number.isInteger(value[key]) || value[key] < 0 || value[key] > 100) throw Error("Invalid draft count");
    out[key] = value[key];
  }
  return out;
}
/** Explicit allowlist: never transfer quotes, prices, tokens or payment secrets. */
export function sanitizeBookingDraft(raw: any): BookingDraft {
  if (!raw || !Array.isArray(raw.routePoints) || raw.routePoints.length < 2 || raw.routePoints.length > 20) throw Error("Invalid route");
  const routePoints = raw.routePoints.map((route: any): RoutePoint => {
    if (!Number.isFinite(route.id) || !["pickup", "dropoff", "stop"].includes(route.type)) throw Error("Invalid route point");
    let point: any = null;
    if (route.point) {
      point = {};
      for (const key of ["description", "place_id", "reference", "name_en", "name_ar", "airport_code", "address"]) {
        if (typeof route.point[key] === "string" && route.point[key].length <= 5000) point[key] = route.point[key];
      }
      if (Number.isFinite(route.point.id)) point.id = route.point.id;
      const coordinates = route.point.coordinates;
      if (coordinates && Number.isFinite(coordinates.lat) && Math.abs(coordinates.lat) <= 90 && Number.isFinite(coordinates.lng) && Math.abs(coordinates.lng) <= 180) point.coordinates = { lat: coordinates.lat, lng: coordinates.lng };
      point.matched_substrings = [];
    }
    return { id: route.id, type: route.type, point };
  });
  const flightDetails = fields(raw.flightDetails, ["flightType", "flightNumber", "airline", "landingTime", "departureTime", "pickupSignName"]);
  if (!["", "arrival", "departure"].includes(flightDetails.flightType)) throw Error("Invalid flight direction");
  return {
    routePoints,
    formDetails: fields(raw.formDetails, ["date", "time"], ["smallSuitcase", "largeSuitcase", "adults", "children", "infants", "numberOfPassengers"]),
    passengerDetails: fields(raw.passengerDetails, ["fullName", "email", "countryCode", "mobileNumber"]),
    childInfantTravel: fields(raw.childInfantTravel, ["infantSeatOption", "childSeatOption"]),
    flightDetails,
    additionalRequirements: fields(raw.additionalRequirements, ["notesToDriver"]),
  };
}
export function saveLanguageDraft(storage: Storage, draft: BookingDraft, destination: string, now = Date.now()) {
  storage.setItem(KEY, JSON.stringify({ destination, expires: now + TTL, draft: sanitizeBookingDraft(draft) }));
}
export function clearLanguageDraft(storage: Storage) { storage.removeItem(KEY); }
export function takeLanguageDraft(storage: Storage, locale: string, now = Date.now()): BookingDraft | null {
  const saved = storage.getItem(KEY);
  storage.removeItem(KEY); // One-time handoff, not ongoing storage of passenger data.
  if (!saved || saved.length > 200000) return null;
  try {
    const value = JSON.parse(saved);
    if (value.destination !== locale || !Number.isFinite(value.expires) || value.expires < now || value.expires > now + TTL) return null;
    return sanitizeBookingDraft(value.draft);
  } catch { return null; }
}
