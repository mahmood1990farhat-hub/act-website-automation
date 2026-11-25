// Render the production map component with a simulated Maps SDK. No browser or provider calls.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

test('selected pins, returned road geometry and camera update across edits', () => {
  const file = path.join(__dirname, '../src/components/_components/bookTaxi/MapView.tsx');
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    fileName: file,
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
    reportDiagnostics: true,
  });
  assert.deepEqual(compiled.diagnostics.filter(d => d.category === ts.DiagnosticCategory.Error), []);

  const pickup = {lat:51.50, lng:-0.15}, stop = {lat:51.52, lng:-0.18}, dropoff = {lat:51.54, lng:-0.17};
  // The road starts/ends near, but not exactly at, the selected entrances.
  const road = [{lat:51.501, lng:-0.151}, {lat:51.52, lng:-0.19}, {lat:51.541, lng:-0.171}];
  const ref = { current: null };
  let flushEffect;
  const element = (type, props) => ({type, props});
  const modules = {
    react: {useMemo: fn => fn(), useRef: () => ref, useCallback: fn => fn, useEffect: fn => { flushEffect = fn; }},
    'react/jsx-runtime': {jsx: element, jsxs: element},
    'next/navigation': {useParams: () => ({locale: 'en'})},
    '@react-google-maps/api': {GoogleMap:'Map', Marker:'Marker', Polyline:'Polyline'},
    '@googlemaps/polyline-codec': {decode: () => road.map(p => [p.lat, p.lng])},
    '@/providers/ProviderMap': {default:'Provider'},
    './booking-text': {bookingText: (_, text) => text},
  };
  class Bounds {
    points = [];
    extend(point) { this.points.push(point); }
    isEmpty() { return this.points.length === 0; }
    getCenter() { return this.points[0]; }
    getSouthWest() { return this.points[0]; }
    getNorthEast() {
      return {equals: p => this.points.every(q => p.lat === q.lat && p.lng === q.lng)};
    }
  }
  const loaded = {};
  new Function('exports', 'require', 'google', compiled.outputText)(
    loaded, name => {
      assert.ok(Object.hasOwn(modules, name), 'Unexpected map dependency: ' + name);
      return modules[name];
    }, {maps: {LatLngBounds: Bounds, Size: class {}, Point: class {}}}
  );
  const fits = [];
  const map = {fitBounds: bounds => fits.push(bounds.points), setCenter() {}, setZoom() {}};
  function render(props) {
    const inner = loaded.default(props).props.children;
    const view = inner.type(inner.props);
    flushEffect();
    return view;
  }
  function markers(view) {
    return view.props.children.flat().filter(c => c && c.type === 'Marker').map(c => c.props);
  }
  function line(view) {
    return view.props.children.flat().find(c => c && c.type === 'Polyline');
  }

  const locations = [pickup, stop, dropoff];
  let view = render({locations});
  view.props.onLoad(map);
  assert.deepEqual(markers(view).map(m => m.position), locations);
  assert.deepEqual(markers(view).map(m => m.label.text), ['Pickup', '1', 'Drop-off']);
  assert.equal(line(view), undefined);
  assert.deepEqual(fits.at(-1), locations);

  view = render({locations, routePolyline:'provider-road'});
  assert.deepEqual(line(view).props.path, road);
  assert.deepEqual(markers(view).map(m => m.position), locations);
  assert.ok(fits.at(-1).some(p => p.lat === road[1].lat && p.lng === road[1].lng));

  view = render({locations: [dropoff, pickup]});
  assert.equal(line(view), undefined);
  assert.deepEqual(markers(view).map(m => m.position), [dropoff, pickup]);
  assert.deepEqual(fits.at(-1), [dropoff, pickup]);

  view = render({routePolyline:'provider-road'});
  assert.deepEqual(markers(view).map(m => m.position), [road[0], road.at(-1)]);
});
