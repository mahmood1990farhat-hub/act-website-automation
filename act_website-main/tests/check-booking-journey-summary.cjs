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
'locations={route.locations}',
'quoteForSelection.expected_trip_duration_minutes'
]) assert.ok(index.includes(expected),"missing journey-summary behavior: "+expected);
assert.equal((index.match(/<MapView\s/g) || []).length, 1, "one shared map for all viewport sizes");
assert.ok(index.includes('route.locations.length ? "block" : "hidden xl:block"'), "small screens show the map only after both endpoints are selected");
assert.ok(map.includes("mapRef.current.fitBounds(bounds);"),"map must refit after async path decode");
console.log("PASS responsive pre-quote journey summary and map-refit wiring");
