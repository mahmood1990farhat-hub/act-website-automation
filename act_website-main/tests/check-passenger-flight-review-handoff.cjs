const assert=require("node:assert/strict"),fs=require("node:fs");
const confirm=fs.readFileSync("src/components/_components/bookTaxi/ConfirmFlightDetails.tsx","utf8");
const passenger=fs.readFileSync("src/components/_components/bookTaxi/PassengerDetails.tsx","utf8");
const flight=fs.readFileSync("src/components/_components/bookTaxi/FlightDetails.tsx","utf8");
const index=fs.readFileSync("src/components/_components/bookTaxi/index.tsx","utf8");

assert.ok(confirm.includes("bodyData.stop_points = stop_points;"),"review/payment handoff must preserve ordered stops");
assert.ok(confirm.includes('customerText(locale, "Pickup Time")'),"pickup time must not be labelled ETA");
assert.ok(!confirm.includes('"vcyHjlwA'),"review map must not contain an unrelated hardcoded route");
assert.ok(confirm.includes('runtimeText(locale, "mapUnavailable")'),"review needs an honest map-unavailable state");
assert.ok(!confirm.includes('{texts.meetAndGreet}</span>'),"review must not claim unselected meet & greet is included");

assert.ok(passenger.includes("isValidPhoneNumber(internationalPhone)"),"passenger phone must be validated");
assert.ok(passenger.includes("emailLooksValid"),"passenger email must be validated before payment");
assert.ok(passenger.includes('maxLength={254}'),"email UI must align with backend guest limit");
assert.ok(passenger.includes('maxLength={32}'),"phone UI must align with backend guest limit");

assert.ok(flight.includes('landingTime: flightType === "arrival" ? flightDetails.landingTime : ""'),"switching to departure must clear stale landing time");
assert.ok(flight.includes('departureTime: flightType === "departure" ? flightDetails.departureTime : ""'),"switching to arrival must clear stale departure time");
assert.ok(index.includes('infantSeatOption: d.infants > 0 ? current.infantSeatOption : ""'),"removed infants must clear stale infant-seat choice");
assert.ok(index.includes('childSeatOption: d.children > 0 ? current.childSeatOption : ""'),"removed children must clear stale child-seat choice");

console.log("PASS passenger/flight/review handoff regression guard");
