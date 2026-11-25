// Run on the website's Node 22+ frontend runtime. No network or provider calls.
const assert = require("node:assert/strict");
const test = require("node:test");
const { selectedPreviewRoute, buildTripQuoteRequest } = require("../src/components/_components/bookTaxi/quote-request.ts");

const selected = (type, id, lat, lng) => ({ type, point: { place_id: id, coordinates: { lat, lng } } });
const pickup = selected("pickup", "A", 51.3, -0.5);
const dropoff = selected("dropoff", "B", 51.5, -0.3);
const stop1 = selected("stop", "C", 51.4, -0.4);
const stop2 = selected("stop", "D", 51.45, -0.35);

test("typing, unresolved details, missing endpoints and invalid coordinates cannot request a route", () => {
  for (const p of [null, { description: "typed" }, { place_id: "A" }, { coordinates: pickup.point.coordinates },
    { place_id: "A", coordinates: { lat: 0, lng: 0 } }, { place_id: "A", coordinates: { lat: 100, lng: 1 } }]) {
    assert.deepEqual(selectedPreviewRoute([{ type: "pickup", point: p }, dropoff]), { locations: [], requestKey: null });
  }
  assert.equal(selectedPreviewRoute([pickup]).requestKey, null);
});

test("a complete address pair yields just geometry before date, time or price", () => {
  const { requestKey, locations } = selectedPreviewRoute([pickup, dropoff]);
  assert.deepEqual(JSON.parse(requestKey), { pickup_location: pickup.point.coordinates, dropoff_location: dropoff.point.coordinates });
  assert.deepEqual(locations, [pickup.point.coordinates, dropoff.point.coordinates]);
  assert.equal(selectedPreviewRoute([{ ...pickup, point: { ...pickup.point, description: "Translated label" } }, dropoff]).requestKey, requestKey);
});

test("partial stop edits clear the old route and keep the resolved pins", () => {
  const preview = selectedPreviewRoute([pickup, stop1, { type: "stop", point: null }, dropoff]);
  assert.equal(preview.requestKey, null);
  assert.deepEqual(preview.locations, [pickup, stop1, dropoff].map(p => p.point.coordinates));
});

test("the quote and preview use identical ordered geometry even with multiple stops", () => {
  const points = [pickup, stop1, stop2, dropoff];
  const before = structuredClone(points);
  const { requestKey } = selectedPreviewRoute(points);
  const geometry = JSON.parse(requestKey);
  const formDetails = { date: "2027-4-1", time: "10:00", numberOfPassengers: 1, smallSuitcase: 0, largeSuitcase: 0 };
  const quote = buildTripQuoteRequest({ routePoints: points, formDetails });
  for (const [key, expected] of Object.entries(geometry)) assert.deepEqual(quote[key], expected);
  assert.deepEqual(geometry.stop_points, [{ point_lat: 51.4, point_lng: -0.4 }, { point_lat: 51.45, point_lng: -0.35 }]);
  assert.deepEqual(points, before);
  assert.notEqual(selectedPreviewRoute([pickup, stop2, stop1, dropoff]).requestKey, requestKey);
  assert.notEqual(selectedPreviewRoute([{ ...dropoff, type: "pickup" }, stop1, stop2, { ...pickup, type: "dropoff" }]).requestKey, requestKey);
});

const { routePreviewQuery, getQuoteProof } = require("../src/components/_components/bookTaxi/route-preview.ts");

test("price submission joins the in-flight preview for the exact route, and accepts failure", async () => {
  const keyA = selectedPreviewRoute([pickup, dropoff]).requestKey;
  const keyB = selectedPreviewRoute([pickup, stop1, dropoff]).requestKey;
  let resolvePreview;
  const pending = new Promise(resolve => { resolvePreview = resolve; });
  let joined = 0;
  const client = {
    getQueryData: () => undefined,
    getQueryState: key => key[1] === keyA ? { fetchStatus: "fetching" } : undefined,
    fetchQuery: options => {
      assert.deepEqual(options.queryKey, ["booking-route-preview", keyA]);
      joined++;
      return pending;
    },
  };
  const result = getQuoteProof(client, keyA);
  assert.equal(joined, 1);
  assert.equal(await getQuoteProof(client, keyB), undefined);
  resolvePreview({ route_proof: "route-A-proof" });
  assert.equal(await result, "route-A-proof");
  assert.equal(joined, 1);
  client.getQueryData = () => ({ route_proof: "cached-proof" });
  assert.equal(await getQuoteProof(client, keyA), "cached-proof");
  assert.equal(joined, 1);
  client.getQueryData = () => undefined;
  client.fetchQuery = async () => { throw new Error("route provider unavailable"); };
  assert.equal(await getQuoteProof(client, keyA), undefined);
});

test("route-only POST consumes flat proof and road line and handles an unavailable preview", async t => {
  const key = selectedPreviewRoute([pickup, stop1, dropoff]).requestKey;
  const opts = routePreviewQuery(key);
  const preview = { route_proof: "signed", route_polyline: "abc" };
  const http = t.mock.method(globalThis, "fetch", async (url, init) => {
    assert.ok(url.endsWith("/api/trips/route-preview/"));
    assert.equal(init.method, "POST");
    assert.deepEqual(JSON.parse(init.body), JSON.parse(key));
    return Response.json(preview);
  });
  const signal = new AbortController().signal;
  assert.deepEqual(await opts.queryFn({ signal }), preview);
  assert.equal(opts.retry, false);
  http.mock.mockImplementation(async () => Response.json({ error: "unavailable" }, { status: 503 }));
  await assert.rejects(opts.queryFn({ signal }));
  http.mock.mockImplementation(async () => Response.json({ route_polyline: "abc" }));
  await assert.rejects(opts.queryFn({ signal }));
});
