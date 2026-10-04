const assert=require("node:assert/strict"),fs=require("node:fs");
const index=fs.readFileSync("src/components/_components/bookTaxi/index.tsx","utf8");
const map=fs.readFileSync("src/components/_components/bookTaxi/MapView.tsx","utf8");
for(const expected of [
'xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]',
'customerText(locale, "Journey summary")',
'customerText(locale, "Pickup")',
'customerText(locale, "Drop-off")',
'customerText(locale, "Passengers")',
'customerText(locale, "Large luggage")',
'customerText(locale, "Small luggage")',
'<MapView routePolyline={rideOptions.route_polyline} />',
'rideOptions.expected_trip_duration_minutes'
]) assert.ok(index.includes(expected),"missing journey-summary behavior: "+expected);
assert.ok(index.includes('className="hidden xl:block sticky top-24"'),"summary must not crowd current mobile form");
assert.ok(map.includes("mapRef.current.fitBounds(bounds);"),"map must refit after async path decode");
console.log("PASS progressive desktop journey summary and map-refit wiring");
