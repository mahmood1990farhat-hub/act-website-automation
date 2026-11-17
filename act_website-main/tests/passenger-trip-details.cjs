/* Actual passenger card, map gate and tracking-map source with controlled hooks.
 * The installed GoogleMap class performs its real mount. Script loading, Maps
 * native objects and effects are local fakes; no browser, HTTP or GPS acceptance.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');
const React = require('react');
const jsx = require('react/jsx-runtime');
const maps = require('@react-google-maps/api');

const root = path.resolve(__dirname, '..');
const cardPath = path.join(root, 'src/components/_components/Trips/MyTripsCard.tsx');
const trip = {
  id: 101, status: 'driver_on_the_way', trip_date: '2030-01-01',
  distance_miles: 1.25, expected_trip_duration_minutes: 5, cost: '12.06',
  pickup_str: 'Synthetic pickup', dropoff_str: 'Synthetic drop-off', route_polyline: '',
  driver_info: {first_name: 'Test', last_name: 'Driver', phone_number: '+440000000001'},
  vehicle_info: {make: 'Test Make', model: 'Test Model', color: 'Silver',
    vehicle_number: 'TEST 101', year_of_manufacture: 2024,
    vehicle_type: {name_en: 'Test Class', name_ar: 'فئة الاختبار'}},
};

function harness(data = trip, locale = 'en') {
  const modules = new Map(), states = new Map();
  let scope, cursor, loader = {isLoaded: false, loadError: undefined}, mapMounts = 0;
  const hooks = {...React, useEffect() {}, useRef: value => ({current: value}),
    useState(initial) {
      const slots = states.get(scope) || [];
      states.set(scope, slots);
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], value => { slots[index] = typeof value === 'function' ? value(slots[index]) : value; }];
    }};
  const button = props => jsx.jsx('button', props);
  const blocked = () => { throw new Error('This display check must not submit requests'); };
  const copy = JSON.parse(fs.readFileSync(path.join(root, `src/dictionaries/${locale}/tripsPassenger.json`)));

  function load(filename) {
    if (modules.has(filename)) return modules.get(filename).exports;
    const module = {exports: {}};
    modules.set(filename, module);
    if (filename.endsWith('.json')) return (module.exports = JSON.parse(fs.readFileSync(filename)));
    const sourcePath = filename === cardPath && process.env.ACT_PASSENGER_CARD_SOURCE
      ? process.env.ACT_PASSENGER_CARD_SOURCE : filename;
    const compiled = ts.transpileModule(fs.readFileSync(sourcePath, 'utf8'), {
      fileName: filename, reportDiagnostics: true,
      compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true},
    });
    assert.equal((compiled.diagnostics || []).filter(x => x.category === ts.DiagnosticCategory.Error).length, 0);
    function resolve(name) {
      if (name === 'react') return hooks;
      if (name === 'react/jsx-runtime') return jsx;
      if (name === 'react-dom') return {createPortal: blocked};
      if (name === '@react-google-maps/api') return {...maps, useJsApiLoader: () => loader};
      if (name === '@googlemaps/polyline-codec') return require(name);
      if (name === 'next/navigation') return {useParams: () => ({locale})};
      if (name === '@tanstack/react-query') return {useQueryClient: () => ({invalidateQueries: blocked})};
      if (name === 'react-toastify') return {toast: {success: blocked, error: blocked}};
      if (name.startsWith('react-icons/')) return new Proxy({}, {get: () => () => null});
      if (name === '@/components/ui/button') return {Button: button};
      if (name === '@/lib/api/postData') return {postData: blocked};
      const base = name.startsWith('@/') ? path.join(root, 'src', name.slice(2))
        : name.startsWith('.') ? path.resolve(path.dirname(filename), name) : null;
      const resolved = base && [base, base + '.ts', base + '.tsx', base + '.json'].find(file => fs.existsSync(file) && fs.statSync(file).isFile());
      if (!resolved) throw new Error('Unexpected test dependency: ' + name);
      return load(resolved);
    }
    new Function('require', 'module', 'exports', compiled.outputText)(resolve, module, module.exports);
    return module.exports;
  }

  const Card = load(cardPath).default;
  function walk(node, key = 'root') {
    if (Array.isArray(node)) return node.map((child, i) => walk(child, key + '/' + i));
    if (!React.isValidElement(node)) return node;
    if (node.type === maps.GoogleMap) {
      const instance = new maps.GoogleMap(node.props);
      instance.setState = (update, callback) => {
        instance.state = {...instance.state, ...(typeof update === 'function' ? update(instance.state, instance.props) : update)};
        if (callback) callback.call(instance);
      };
      instance.getRef({});
      instance.componentDidMount();
      return walk(instance.render(), key + '/GoogleMap');
    }
    if (typeof node.type === 'function') {
      const previous = [scope, cursor];
      scope = key; cursor = 0;
      const child = node.type(node.props);
      [scope, cursor] = previous;
      return walk(child, key + '/child');
    }
    return {...node, props: {...node.props, children: walk(node.props.children, key + '/children')}};
  }
  const render = () => walk(jsx.jsx(Card, {data, locale, token: 'synthetic-token', trans: copy.deleteTrip, tripCardTrans: copy.tripCard}));
  const click = (tree, label) => {
    const target = flatten(tree).find(node => node?.type === 'button' && text(node).includes(label));
    assert.ok(target, 'Expected button: ' + label);
    target.props.onClick({stopPropagation() {}});
    return render();
  };
  return {render, click, detailsLabel: copy.tripCard.seeDetails,
    ready() {
      global.google = {maps: {Map: class {
        constructor() { mapMounts++; }
        setCenter() {} setZoom() {} panTo() {}
      }}};
      loader = {isLoaded: true};
    },
    fail() { loader = {isLoaded: false, loadError: new Error('Synthetic script failure')}; },
    get mapMounts() { return mapMounts; },
  };
}
function flatten(node) {
  return Array.isArray(node) ? node.flatMap(flatten) : React.isValidElement(node)
    ? [node, ...flatten(node.props.children)] : [node];
}
function text(node) { return flatten(node).filter(x => typeof x === 'string' || typeof x === 'number').join(' ').replace(/\s+/g, ' ').trim(); }

for (const status of ['driver_on_the_way', 'active']) {
  test(`${status}: Details waits for Maps on a fresh passenger visit, then mounts`, () => {
    delete global.google;
    const h = harness({...trip, status});
    const details = h.click(h.render(), h.detailsLabel);
    assert.match(text(details), /Trip Details/);
    assert.equal(h.mapMounts, 0);
    assert.ok(flatten(details).some(node => node?.props?.className === 'sr-only'), 'Existing map-loading feedback remains visible to assistive technology');
    try {
      h.ready();
      assert.match(text(h.render()), /Connecting to trip tracking/);
      assert.equal(h.mapMounts, 1);
    } finally { delete global.google; }
  });
}

test('Maps load failure stays inside closable passenger details', () => {
  delete global.google;
  const h = harness();
  h.fail();
  const details = h.click(h.render(), h.detailsLabel);
  const runtimeCopy = JSON.parse(fs.readFileSync(path.join(root, 'src/dictionaries/customer-runtime.json')));
  assert.ok(text(details).includes(runtimeCopy.en.mapUnavailable));
  assert.equal(h.mapMounts, 0);
  assert.doesNotMatch(text(h.click(details, 'Close')), /Trip Details/);
});

test('registered driver phone and vehicle fields use the existing passenger API values', () => {
  const h = harness();
  const summary = text(h.render());
  for (const value of ['+440000000001', 'Test Make', 'TEST 101', '2024', 'Vehicle class', 'Test Class']) assert.ok(summary.includes(value), value);
  assert.match(summary, /£\s*12\.06/);
  const details = text(h.click(h.render(), h.detailsLabel));
  assert.ok(details.includes('+440000000001'));
});

test('guest driver and vehicle fallback fields remain supported', () => {
  const h = harness({...trip, driver_info: undefined, guest_driver_phone: '+440000000002',
    vehicle_info: {brand: 'Guest Make', registration_number: 'GUEST 101', year: 2023}});
  const summary = text(h.render());
  for (const value of ['+440000000002', 'Guest Make', 'GUEST 101', '2023']) assert.ok(summary.includes(value), value);
});

test('Arabic class label and class name stay distinct from the vehicle make', () => {
  const summary = text(harness(trip, 'ar').render());
  for (const value of ['فئة السيارة', 'فئة الاختبار', 'Test Make']) assert.ok(summary.includes(value), value);
});
