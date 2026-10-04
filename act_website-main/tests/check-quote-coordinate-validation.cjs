// Isolated production quote-builder tests: no browser, network, database or payment.
// Run from act_website-main: node --test tests/check-quote-coordinate-validation.cjs
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const sourcePath = path.resolve(__dirname, '../src/components/_components/bookTaxi/quote-request.ts');
const source = fs.readFileSync(sourcePath, 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  reportDiagnostics: true,
});
const errors = (compiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error);
assert.equal(errors.length, 0, 'Production helper must transpile without syntax errors');
const loaded = new Module(sourcePath, module);
loaded.filename = sourcePath;
loaded.paths = module.paths;
loaded._compile(compiled.outputText, sourcePath);
const { buildTripQuoteRequest, hasValidCoordinates, locationValidationMessage } = loaded.exports;
const countValidationMessage = 'Please check the passenger and luggage counts before requesting a price.';
const point = (lat, lng) => ({ coordinates: { lat, lng } });
const input = () => ({
  routePoints: [
    { type: 'pickup', point: point(51.47, -0.4543) },
    { type: 'dropoff', point: point(51.5074, -0.1278) },
  ],
  formDetails: { date: '2026-11-5', time: '00:05', numberOfPassengers: 3, largeSuitcase: 2, smallSuitcase: 1 },
});
const reject = value => assert.throws(() => buildTripQuoteRequest(value), { message: locationValidationMessage });

test('valid route preserves existing quote payload and fee options', () => {
  assert.deepEqual(buildTripQuoteRequest(input()), {
    pickup_location: { lat: 51.47, lng: -0.4543 },
    dropoff_location: { lat: 51.5074, lng: -0.1278 },
    trip_date: '2026-11-05', trip_time: '00:05', passengers_count: 3,
    large_suitcase: 2, small_suitcase: 1,
    booking_details: { additional_requirements: { meet_and_greet: false } },
  });
});
test('no optional stop_points field is sent when there are no stops', () => {
  assert.equal(Object.hasOwn(buildTripQuoteRequest(input()), 'stop_points'), false);
});
test('valid stops retain order and coordinate field names', () => {
  const value = input();
  value.routePoints.splice(1, 0,
    { type: 'stop', point: point(51.5, -0.2) },
    { type: 'stop', point: point(51.6, -0.1) });
  assert.deepEqual(buildTripQuoteRequest(value).stop_points, [
    { point_lat: 51.5, point_lng: -0.2 },
    { point_lat: 51.6, point_lng: -0.1 },
  ]);
});
test('quote construction does not mutate form or route input', () => {
  const value = input();
  const before = structuredClone(value);
  buildTripQuoteRequest(value);
  assert.deepEqual(value, before);
});
for (const [name, coords] of [
  ['positive latitude outside range', [90.01, 1]],
  ['negative latitude outside range', [-90.01, 1]],
  ['positive longitude outside range', [1, 180.01]],
  ['negative longitude outside range', [1, -180.01]],
]) {
  for (const endpoint of ['pickup', 'dropoff']) {
    test(`${endpoint}: rejects ${name}`, () => {
      const value = input();
      value.routePoints.find(p => p.type === endpoint).point = point(...coords);
      reject(value);
    });
  }
}
for (const [name, value] of [
  ['missing point', null], ['missing coordinates', {}],
  ['nonfinite latitude', point(NaN, -0.1)], ['infinite longitude', point(51, Infinity)],
  ['numeric strings', point('51.5', '-0.1')], ['null latitude', point(null, -0.1)],
  ['existing zero/zero sentinel', point(0, 0)],
]) {
  test(`coordinate helper rejects ${name}`, () => assert.equal(hasValidCoordinates(value), false));
}
for (const [lat, lng] of [[51.5, 0], [0, 1], [90, 180], [-90, -180]]) {
  test(`valid coordinate boundary/axis remains accepted: ${lat}, ${lng}`, () => {
    assert.equal(hasValidCoordinates(point(lat, lng)), true);
  });
}
for (const [name, value] of [
  ['empty added stop', null], ['stop without coordinates', {}],
  ['stop with missing longitude', { coordinates: { lat: 51.5 } }],
  ['stop with numeric strings', point('51.5', '-0.1')],
  ['stop with nonfinite latitude', point(NaN, -0.1)],
  ['stop with impossible latitude', point(95, -0.1)],
  ['stop with impossible longitude', point(51.5, 185)],
  ['stop with zero/zero sentinel', point(0, 0)],
]) {
  test(`quote builder rejects ${name}`, () => {
    const valueWithStop = input();
    valueWithStop.routePoints.splice(1, 0, { type: 'stop', point: value });
    reject(valueWithStop);
  });
}
for (const endpoint of ['pickup', 'dropoff']) {
  test(`quote builder rejects missing ${endpoint}`, () => {
    const value = input();
    value.routePoints = value.routePoints.filter(p => p.type !== endpoint);
    reject(value);
  });
}

for (const [name, counts] of [
  ['zero passengers', { numberOfPassengers: 0 }],
  ['more than seven passengers', { numberOfPassengers: 8 }],
  ['fractional passengers', { numberOfPassengers: 1.5 }],
  ['negative large luggage', { largeSuitcase: -1 }],
  ['negative small luggage', { smallSuitcase: -1 }],
  ['fractional luggage', { largeSuitcase: 1.5 }],
  ['more than eight total suitcases', { largeSuitcase: 5, smallSuitcase: 4 }],
]) {
  test(`quote builder rejects ${name}`, () => {
    const value = input();
    Object.assign(value.formDetails, counts);
    assert.throws(() => buildTripQuoteRequest(value), { message: countValidationMessage });
  });
}
test('quote builder accepts seven passengers and eight total suitcases', () => {
  const value = input();
  Object.assign(value.formDetails, { numberOfPassengers: 7, largeSuitcase: 4, smallSuitcase: 4 });
  assert.equal(buildTripQuoteRequest(value).passengers_count, 7);
});
