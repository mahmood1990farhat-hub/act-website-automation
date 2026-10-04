// Static regression guard for quote invalidation wiring. No network/provider calls.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const index = fs.readFileSync("src/components/_components/bookTaxi/index.tsx","utf8");
const route = fs.readFileSync("src/components/_components/bookTaxi/RoutePoints.tsx","utf8");
for (const expected of [
  "setRideOptions(null);",
  "setSelectedCar(undefined);",
  'setClientSecret("");',
  "setPaymentTotal(null);",
  "resetQuoteState={() =>",
]) assert.ok(index.includes(expected), "missing BookTaxi reset: "+expected);
assert.ok(route.includes("resetQuoteState: () => void;"), "RoutePoints prop contract missing");
const resetAt=route.indexOf("resetQuoteState();");
const fetchAt=route.indexOf("const response = await fetch(");
assert.ok(resetAt >= 0 && fetchAt > resetAt, "quote state must reset before quote request");
console.log("PASS quote recalculation invalidates quote, selected vehicle, payment secret and payment total before request");
