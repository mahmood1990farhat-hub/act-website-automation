/*
 * Controlled effect simulation of the actual tracking consumers.
 * No application/server/browser/provider is started. Every WebSocket, Maps
 * component and animation frame is a local recording fake. This is not browser,
 * connected journey, native-device or environment-isolation acceptance.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '../..');
const sourcePaths = {
  helper: 'src/lib/trip-tracking-url.ts',
  provider: 'src/components/_components/dashboard/tracking/trip-tracking-provider.tsx',
  hook: 'src/hooks/use-trip-tracking.ts',
};
const compiled = Object.fromEntries(Object.entries(sourcePaths).map(([name, file]) => {
  const result = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    fileName: file,
    reportDiagnostics: true,
    compilerOptions: {
      target: ts.ScriptTarget.ES2020,
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
      isolatedModules: true,
    },
  });
  const errors = (result.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error);
  assert.equal(errors.length, 0, `${file}: ${errors.map(d => ts.flattenDiagnosticMessageText(d.messageText, '\n')).join('\n')}`);
  return [name, result.outputText];
}));

const plain = value => value === undefined ? undefined : JSON.parse(JSON.stringify(value));
const LOCATION = {lat: 51.501, lng: -0.141};
const NEXT_LOCATION = {lat: 51.503, lng: -0.139};
const ROUTE = [[51.49, -0.16], [51.50, -0.15]];
const cases = [];
const test = (name, run) => cases.push({name, run});

function createHarness(kind, apiBaseUrl, initialProps = {}) {
  const slots = [];
  const sockets = [];
  const stateWrites = [];
  const refWrites = [];
  const logs = [];
  const frames = new Map();
  let frameId = 0;
  let cursor = 0;
  let pending = [];
  let dirty = false;
  let activeEffect = null;
  let props = {tripId: '101', routePolyline: '', ...initialProps};
  let output;
  let renderFunction;

  function slot(type, initialise) {
    const index = cursor++;
    if (!slots[index]) slots[index] = {type, ...initialise(index)};
    assert.equal(slots[index].type, type, `Hook order changed at slot ${index}`);
    return [slots[index], index];
  }

  const react = {
    __esModule: true,
    useState(initial) {
      const [entry, index] = slot('state', () => ({value: typeof initial === 'function' ? initial() : initial}));
      if (!entry.set) entry.set = next => {
        const value = typeof next === 'function' ? next(entry.value) : next;
        stateWrites.push({index, value: plain(value)});
        if (!Object.is(entry.value, value)) dirty = true;
        entry.value = value;
      };
      return [entry.value, entry.set];
    },
    useRef(initial) {
      const [entry] = slot('ref', index => {
        let value = initial;
        const ref = {};
        Object.defineProperty(ref, 'current', {
          enumerable: true,
          get: () => value,
          set: next => {
            refWrites.push({index, value: plain(next)});
            value = next;
          },
        });
        return {ref};
      });
      return entry.ref;
    },
    useEffect(callback, deps) {
      const [entry, index] = slot('effect', () => ({deps: undefined, cleanup: undefined}));
      const changed = !deps || !entry.deps || deps.length !== entry.deps.length ||
        deps.some((value, i) => !Object.is(value, entry.deps[i]));
      if (changed) pending.push({entry, index, callback, deps});
    },
  };
  react.default = react;

  class RecordingWebSocket {
    constructor(url) {
      this.url = url;
      this.ownerEffect = activeEffect;
      this.closeCalls = 0;
      this.onopen = null;
      this.onmessage = null;
      this.onclose = null;
      this.onerror = null;
      sockets.push(this);
    }
    close() {
      this.closeCalls += 1;
      if (this.onclose) this.onclose({type: 'close'});
    }
  }

  const jsx = (type, properties, key) => ({type, props: properties || {}, key});
  const context = vm.createContext({
    URL,
    process: {env: {NEXT_PUBLIC_API_BASE_URL: apiBaseUrl}},
    WebSocket: RecordingWebSocket,
    console: Object.fromEntries(['log', 'warn', 'error'].map(level => [level, (...args) => logs.push({level, args})])),
    requestAnimationFrame(callback) {
      const id = ++frameId;
      frames.set(id, callback);
      return id;
    },
    cancelAnimationFrame(id) { frames.delete(id); },
    google: {maps: {
      Size: class { constructor(width, height) { this.width = width; this.height = height; } },
      Point: class { constructor(x, y) { this.x = x; this.y = y; } },
    }},
  });
  const modules = {};
  function load(name) {
    if (modules[name]) return modules[name].exports;
    const module = {exports: {}};
    modules[name] = module;
    const requireFake = specifier => {
      if (specifier === 'react') return react;
      if (specifier === 'react/jsx-runtime') return {jsx, jsxs: jsx, Fragment: 'Fragment'};
      if (specifier === '@react-google-maps/api') return {GoogleMap: 'GoogleMap', Marker: 'Marker', Polyline: 'Polyline'};
      if (specifier === '@googlemaps/polyline-codec') return {
        decode(polyline) {
          assert.equal(polyline, 'synthetic-route-a', 'Only the declared synthetic route may be decoded');
          return ROUTE;
        },
      };
      if (specifier === '@/lib/trip-tracking-url') return load('helper');
      throw new Error(`Unexpected import blocked: ${specifier}`);
    };
    const wrapper = new vm.Script(`(function(require, module, exports) {\n${compiled[name]}\n})`, {filename: sourcePaths[name]});
    wrapper.runInContext(context)(requireFake, module, module.exports);
    return module.exports;
  }
  const actual = load(kind);
  renderFunction = kind === 'provider' ? () => actual.default(props) : () => actual.useTripTracking(props.tripId);

  function render() {
    cursor = 0;
    pending = [];
    dirty = false;
    output = renderFunction();
    const changed = pending;
    // React cleans up changed passive effects before their replacement setups.
    for (const {entry} of changed) {
      if (entry.cleanup) entry.cleanup();
      entry.cleanup = undefined;
    }
    for (const {entry, index, callback, deps} of changed) {
      entry.deps = deps;
      activeEffect = index;
      entry.cleanup = callback();
      activeEffect = null;
      assert.ok(entry.cleanup === undefined || typeof entry.cleanup === 'function');
    }
  }
  function flush() {
    let attempts = 0;
    while (dirty) {
      assert.ok(++attempts <= 12, 'Effect simulation did not settle');
      render();
    }
    return output;
  }
  render();
  flush();

  const harness = {
    kind, sockets, stateWrites, refWrites, logs,
    get output() { return output; },
    update(next) {
      props = {...props, ...next};
      render();
      return flush();
    },
    flush,
    emitLocation(socket, location = LOCATION) {
      assert.equal(typeof socket.onmessage, 'function');
      socket.onmessage({data: JSON.stringify(kind === 'provider' ? {location: {...location, heading: 91}} : location)});
      flush();
    },
    advanceFrame() {
      const next = frames.entries().next();
      assert.equal(next.done, false, 'Expected a scheduled animation frame');
      const [id, callback] = next.value;
      frames.delete(id);
      callback(0);
      flush();
    },
    refs() { return slots.filter(s => s.type === 'ref').map(s => plain(s.ref.current)); },
    cleanupFor(socket) {
      const cleanup = slots[socket.ownerEffect].cleanup;
      assert.equal(typeof cleanup, 'function');
      return cleanup;
    },
    unmount() {
      for (const entry of slots) {
        if (entry.type === 'effect' && entry.cleanup) {
          const cleanup = entry.cleanup;
          entry.cleanup = undefined;
          cleanup();
        }
      }
      assert.equal(frames.size, 0, 'Unmount left a synthetic animation frame scheduled');
    },
  };
  return harness;
}

function withHarness(kind, base, props, run) {
  const harness = createHarness(kind, base, props);
  try { run(harness); } finally { harness.unmount(); }
}

function assertReset(h) {
  if (h.kind === 'hook') {
    assert.equal(h.output.location, null);
    assert.equal(h.output.connected, false);
  } else {
    assert.deepEqual(plain(h.output.props.center), {lat: 0, lng: 0});
    assert.ok(!h.refs().some(value => JSON.stringify(value) === JSON.stringify(LOCATION)), 'Previous trip target remained in a map ref');
  }
}

for (const kind of ['provider', 'hook']) {
  test(`${kind}: configured HTTPS origin, port and root tracking route`, () => {
    withHarness(kind, 'https://staging.example.invalid:9443/api/v1/', {}, h => {
      assert.equal(h.sockets.length, 1);
      assert.equal(h.sockets[0].url, 'wss://staging.example.invalid:9443/ws/trips/101/tracking/');
    });
  });

  test(`${kind}: configured loopback HTTP uses WS and retains port`, () => {
    withHarness(kind, 'http://127.0.0.1:8123/api/', {}, h => {
      assert.equal(h.sockets.length, 1);
      assert.equal(h.sockets[0].url, 'ws://127.0.0.1:8123/ws/trips/101/tracking/');
    });
  });

  test(`${kind}: missing and malformed API configuration creates no socket`, () => {
    for (const base of [undefined, '', '/api/', 'https:/staging.example.invalid/api', 'https://user:pass@staging.example.invalid/api']) {
      withHarness(kind, base, {}, h => assert.equal(h.sockets.length, 0, `Unexpected socket for ${String(base)}`));
    }
  });

  test(`${kind}: invalid trip identifier creates no socket`, () => {
    for (const tripId of ['', '../202', '101?next=202', '101/202']) {
      withHarness(kind, 'https://staging.example.invalid/api', {tripId}, h => assert.equal(h.sockets.length, 0));
    }
  });

  test(`${kind}: cleanup detaches handlers and suppresses captured late callbacks`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const socket = h.sockets[0];
      const captured = Object.fromEntries(['onopen', 'onmessage', 'onclose', 'onerror'].map(name => [name, socket[name]]));
      if (socket.onopen) socket.onopen({type: 'open'});
      h.emitLocation(socket);
      assert.ok(h.stateWrites.length > 0, 'Expected active-session state writes');
      const cleanup = h.cleanupFor(socket);
      cleanup();
      assert.equal(socket.closeCalls, 1);
      for (const name of ['onopen', 'onmessage', 'onclose', 'onerror']) assert.equal(socket[name], null, `${name} remains attached`);
      const baseline = {state: h.stateWrites.length, refs: h.refWrites.length, logs: h.logs.length};
      if (captured.onopen) captured.onopen({type: 'open'});
      captured.onmessage({data: JSON.stringify(kind === 'provider' ? {location: NEXT_LOCATION} : NEXT_LOCATION)});
      if (captured.onclose) captured.onclose({type: 'close'});
      if (captured.onerror) captured.onerror({type: 'error'});
      assert.deepEqual({state: h.stateWrites.length, refs: h.refWrites.length, logs: h.logs.length}, baseline);
    });
  });

  test(`${kind}: changing trips closes the old socket and clears old display state`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const first = h.sockets[0];
      if (first.onopen) first.onopen({type: 'open'});
      h.emitLocation(first);
      if (kind === 'provider') h.advanceFrame();
      h.update({tripId: '202'});
      assert.equal(first.closeCalls, 1);
      assert.equal(h.sockets.length, 2);
      assert.equal(h.sockets[1].url, 'wss://staging.example.invalid/ws/trips/202/tracking/');
      assert.equal(h.sockets[1].closeCalls, 0);
      assertReset(h);
    });
  });

  test(`${kind}: replaying an old cleanup cannot close the replacement socket`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const first = h.sockets[0];
      const oldCleanup = h.cleanupFor(first);
      h.update({tripId: '202'});
      const replacement = h.sockets[1];
      oldCleanup();
      assert.equal(first.closeCalls, 2);
      assert.equal(replacement.closeCalls, 0);
    });
  });

  test(`${kind}: valid-to-invalid trip transition closes without fallback`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const first = h.sockets[0];
      if (first.onopen) first.onopen({type: 'open'});
      h.emitLocation(first);
      if (kind === 'provider') h.advanceFrame();
      h.update({tripId: ''});
      assert.equal(first.closeCalls, 1);
      assert.equal(h.sockets.length, 1);
      assertReset(h);
    });
  });
}

test('provider: a different trip with the same polyline resets pending targets and route position', () => {
  withHarness('provider', 'https://staging.example.invalid/api', {routePolyline: 'synthetic-route-a'}, h => {
    h.emitLocation(h.sockets[0]);
    h.advanceFrame();
    assert.notDeepEqual(plain(h.output.props.center), {lat: ROUTE[0][0], lng: ROUTE[0][1]});
    h.update({tripId: '202'});
    assert.deepEqual(plain(h.output.props.center), {lat: ROUTE[0][0], lng: ROUTE[0][1]});
    assert.ok(!h.refs().some(value => JSON.stringify(value) === JSON.stringify(LOCATION)), 'Previous pending location survived a same-polyline trip change');
  });
});

console.log('Controlled effect simulation: real source, fake transport/Maps/animation; no browser or connected acceptance.');
let failed = 0;
for (const [index, entry] of cases.entries()) {
  try {
    entry.run();
    console.log(`ok ${index + 1} - ${entry.name}`);
  } catch (error) {
    failed += 1;
    console.error(`not ok ${index + 1} - ${entry.name}`);
    console.error(error.stack || error);
  }
}
console.log(`1..${cases.length}`);
console.log(`Effect simulation: ${cases.length - failed} passed, ${failed} failed (${cases.length} named cases).`);
if (failed) process.exitCode = 1;
