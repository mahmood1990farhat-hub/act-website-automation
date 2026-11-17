/*
 * Controlled effect simulation of the actual tracking consumers.
 * No application/server/browser/provider is started. Every WebSocket, Maps
 * component, clock and animation frame is a local recording fake. This is not browser,
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
const TOKEN = 'synthetic-viewer-token';
const cases = [];
const test = (name, run) => cases.push({name, run});

function createHarness(kind, apiBaseUrl, initialProps = {}) {
  const slots = [];
  const sockets = [];
  const stateWrites = [];
  const refWrites = [];
  const logs = [];
  const frames = new Map();
  const timers = new Map();
  let frameId = 0;
  let timerId = 0;
  let clock = Date.parse('2026-11-06T12:10:00.000Z');
  let cursor = 0;
  let pending = [];
  let dirty = false;
  let activeEffect = null;
  let props = {tripId: '101', routePolyline: '', token: TOKEN, locale: 'en', ...initialProps};
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
      if (props.transportFailure === 'construct') throw new Error('Synthetic socket construction failure');
      this.url = url;
      this.ownerEffect = activeEffect;
      this.closeCalls = 0;
      this.messages = [];
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
    send(message) {
      if (props.transportFailure === 'send') throw new Error('Synthetic socket send failure');
      this.messages.push(JSON.parse(message));
    }
  }

  const jsx = (type, properties, key) => ({type, props: properties || {}, key});
  const context = vm.createContext({
    URL,
    Date: class extends Date { static now() { return clock; } },
    setTimeout(callback, delay) {
      const id = ++timerId;
      timers.set(id, {callback, deadline: clock + delay});
      return id;
    },
    clearTimeout(id) { timers.delete(id); },
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
      if (specifier === '@/hooks/use-trip-tracking') return load('hook');
      throw new Error(`Unexpected import blocked: ${specifier}`);
    };
    const wrapper = new vm.Script(`(function(require, module, exports) {\n${compiled[name]}\n})`, {filename: sourcePaths[name]});
    wrapper.runInContext(context)(requireFake, module, module.exports);
    return module.exports;
  }
  const actual = load(kind);
  renderFunction = kind === 'provider' ? () => actual.default(props) : () => actual.useTripTracking(props.tripId, props.token);

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
    get now() { return clock; },
    get timerCount() { return timers.size; },
    update(next) {
      props = {...props, ...next};
      render();
      return flush();
    },
    flush,
    emit(socket, data) {
      assert.equal(typeof socket.onmessage, 'function');
      socket.onmessage({data: JSON.stringify(data)});
      flush();
    },
    authenticate(socket = sockets.at(-1)) {
      socket.onopen({type: 'open'});
      this.emit(socket, {type: 'auth_ok', role: 'viewer'});
    },
    emitLocation(socket, location = LOCATION, age = 0) {
      this.emit(socket, {type: 'location', location: {...location, heading: 91, received_at: new Date(clock - age).toISOString()}});
    },
    advanceTime(milliseconds) {
      const target = clock + milliseconds;
      for (;;) {
        const next = [...timers.entries()].sort((a, b) => a[1].deadline - b[1].deadline)[0];
        if (!next || next[1].deadline > target) break;
        const [id, {callback, deadline}] = next;
        clock = deadline;
        timers.delete(id);
        callback();
        flush();
      }
      clock = target;
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
      assert.equal(timers.size, 0, 'Unmount left a location freshness timer scheduled');
    },
  };
  return harness;
}

function withHarness(kind, base, props, run) {
  const harness = createHarness(kind, base, props);
  try { run(harness); } finally { harness.unmount(); }
}

function elements(node, predicate) {
  if (!node || typeof node !== 'object') return [];
  if (Array.isArray(node)) return node.flatMap(child => elements(child, predicate));
  return [...(predicate(node) ? [node] : []), ...elements(node.props?.children, predicate)];
}
const mapElement = h => elements(h.output, node => node.type === 'GoogleMap')[0];
const carMarkers = h => elements(h.output, node => node.type === 'Marker' && node.props.icon?.url === '/images/car2.svg');
const statusMessage = h => elements(h.output, node => node.props?.role === 'status')[0]?.props.children;

function assertStatus(h, status, message) {
  if (h.kind === 'hook') assert.equal(h.output.status, status);
  else assert.equal(statusMessage(h), message);
}

function assertReset(h) {
  if (h.kind === 'hook') {
    assert.equal(h.output.location, null);
    assert.equal(h.output.connected, false);
  } else {
    assert.equal(carMarkers(h).length, 0, 'Old driver marker remains displayed');
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
      h.authenticate(socket);
      h.emitLocation(socket);
      assert.ok(h.stateWrites.length > 0, 'Expected active-session state writes');
      const cleanup = h.cleanupFor(socket);
      cleanup();
      assert.equal(socket.closeCalls, 1);
      for (const name of ['onopen', 'onmessage', 'onclose', 'onerror']) assert.equal(socket[name], null, `${name} remains attached`);
      const baseline = {state: h.stateWrites.length, refs: h.refWrites.length, logs: h.logs.length};
      if (captured.onopen) captured.onopen({type: 'open'});
      captured.onmessage({data: JSON.stringify({type: 'location', location: {...NEXT_LOCATION, received_at: new Date(h.now).toISOString()}})});
      if (captured.onclose) captured.onclose({type: 'close'});
      if (captured.onerror) captured.onerror({type: 'error'});
      assert.deepEqual({state: h.stateWrites.length, refs: h.refWrites.length, logs: h.logs.length}, baseline);
    });
  });

  test(`${kind}: changing trips closes the old socket and clears old display state`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const first = h.sockets[0];
      h.authenticate(first);
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
      h.authenticate(first);
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
    h.authenticate();
    h.emitLocation(h.sockets[0]);
    h.advanceFrame();
    assert.deepEqual(plain(mapElement(h).props.center), LOCATION);
    h.update({tripId: '202'});
    assert.deepEqual(plain(mapElement(h).props.center), {lat: ROUTE[1][0], lng: ROUTE[1][1]});
    assert.equal(carMarkers(h).length, 0, 'Route preview fabricated a driver marker');
    assert.ok(!h.refs().some(value => JSON.stringify(value) === JSON.stringify(LOCATION)), 'Previous pending location survived a same-polyline trip change');
  });
});

for (const kind of ['provider', 'hook']) {
  test(`${kind}: missing viewer token opens no socket and explains sign-in requirement`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {token: undefined}, h => {
      assert.equal(h.sockets.length, 0);
      assertReset(h);
      assertStatus(h, 'unauthorized', 'Tracking access was not authorised. Sign in again to the account for this trip.');
    });
  });

  test(`${kind}: transport open sends viewer authentication but never grants location access`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const socket = h.sockets[0];
      assert.equal(socket.url.includes(TOKEN), false, 'Viewer token leaked into URL');
      socket.onopen({type: 'open'});
      assert.deepEqual(socket.messages, [{type: 'viewer_auth', access: TOKEN}]);
      h.emitLocation(socket);
      h.emit(socket, {type: 'auth_ok', role: 'driver'});
      h.emitLocation(socket);
      assertReset(h);
      assert.equal(h.timerCount, 1, 'Unauthenticated socket must have a bounded authentication timeout');
      assertStatus(h, 'connecting', 'Connecting to trip tracking…');
      assert.equal(JSON.stringify(h.logs).includes(TOKEN), false, 'Viewer token leaked into logs');
    });
  });

  test(`${kind}: viewer confirmation accepts the real nested location envelope including zero coordinates`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      h.authenticate();
      assertStatus(h, 'waiting', 'Waiting for a fresh driver location…');
      if (kind === 'hook') assert.equal(h.output.connected, true);
      h.emitLocation(h.sockets[0], {lat: 0, lng: 0});
      if (kind === 'provider') {
        h.advanceFrame();
        assert.deepEqual(plain(carMarkers(h)[0].props.position), {lat: 0, lng: 0});
      } else {
        assert.deepEqual(plain(h.output.location), {lat: 0, lng: 0, heading: 91});
      }
      assertStatus(h, 'live', 'Live driver location');
    });
  });

  test(`${kind}: legacy, invalid and old coordinates cannot become a fresh driver position`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const socket = h.sockets[0];
      h.authenticate(socket);
      for (const data of [null, {}, {type: 'location', location: LOCATION},
        {type: 'location', location: {...LOCATION, received_at: 'invalid'}},
        {type: 'location', location: {lat: '51', lng: -1, received_at: new Date(h.now).toISOString()}},
        {type: 'location', location: {lat: 91, lng: 0, received_at: new Date(h.now).toISOString()}},
        {type: 'location', location: {lat: 0, lng: 181, received_at: new Date(h.now).toISOString()}}]) h.emit(socket, data);
      socket.onmessage({data: 'invalid JSON'});
      h.emitLocation(socket, LOCATION, 30_000);
      h.emitLocation(socket, LOCATION, -6_000);
      if (kind === 'provider') assert.equal(carMarkers(h).length, 0);
      else assert.equal(h.output.location, null);
      assert.equal(h.timerCount, 0);
      assertStatus(h, 'waiting', 'Waiting for a fresh driver location…');
    });
  });

  test(`${kind}: cached receipt age limits remaining freshness and a fresh update recovers`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const socket = h.sockets[0];
      h.authenticate(socket);
      h.emitLocation(socket, LOCATION, 20_000);
      if (kind === 'provider') h.advanceFrame();
      h.advanceTime(9_999);
      assertStatus(h, 'live', 'Live driver location');
      h.advanceTime(1);
      assertStatus(h, 'stale', 'Driver location is out of date. Waiting for an update…');
      if (kind === 'provider') {
        assert.equal(carMarkers(h).length, 0);
        h.advanceFrame();
        assert.equal(carMarkers(h).length, 0, 'Animation revived an expired position');
      } else {
        assert.equal(h.output.location, null);
        assert.equal(h.output.connected, true, 'Stale GPS must not pretend the authorised socket disconnected');
      }
      h.emitLocation(socket, NEXT_LOCATION);
      if (kind === 'provider') {
        h.advanceFrame();
        assert.deepEqual(plain(carMarkers(h)[0].props.position), NEXT_LOCATION);
      }
      assertStatus(h, 'live', 'Live driver location');
      assert.equal(h.timerCount, 1);
    });
  });

  test(`${kind}: refusal, completion and cancellation clear the position and cannot be undone by late frames`, () => {
    for (const [frame, status, message] of [
      [{type: 'auth_error'}, 'unauthorized', 'Tracking access was not authorised. Sign in again to the account for this trip.'],
      [{type: 'ended', reason: 'completed'}, 'completed', 'Trip completed. Tracking has stopped.'],
      [{type: 'ended', reason: 'cancelled'}, 'cancelled', 'Trip cancelled. Tracking has stopped.'],
    ]) {
      withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
        const socket = h.sockets[0];
        h.authenticate(socket);
        h.emitLocation(socket);
        if (kind === 'provider') h.advanceFrame();
        h.emit(socket, frame);
        assert.equal(socket.closeCalls, 1);
        assertReset(h);
        assertStatus(h, status, message);
        h.emit(socket, {type: 'auth_ok', role: 'viewer'});
        h.emitLocation(socket, NEXT_LOCATION);
        if (kind === 'provider') h.advanceFrame();
        assertReset(h);
        assertStatus(h, status, message);
        assert.equal(h.timerCount, 0);
      });
    }
  });

  test(`${kind}: socket disconnection removes the last marker and displays a recovery instruction`, () => {
    for (const callback of ['onclose', 'onerror']) {
      withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
        const socket = h.sockets[0];
        h.authenticate(socket);
        h.emitLocation(socket);
        if (kind === 'provider') h.advanceFrame();
        socket[callback]({type: callback});
        h.flush();
        assertReset(h);
        assertStatus(h, 'disconnected', 'Tracking disconnected. Reopen the trip to reconnect.');
        assert.equal(h.sockets.length, 1, 'Failure unexpectedly opened another socket');
        assert.equal(h.timerCount, 0);
      });
    }
  });

  test(`${kind}: changing the viewer token closes the prior session and requires new authorisation`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const old = h.sockets[0];
      h.authenticate(old);
      h.emitLocation(old);
      if (kind === 'provider') h.advanceFrame();
      h.update({token: 'synthetic-replacement-token'});
      assertReset(h);
      assert.equal(old.closeCalls, 1);
      assert.equal(old.onmessage, null);
      assert.equal(h.timerCount, 1, 'Only the replacement authentication timeout should remain');
      const replacement = h.sockets[1];
      replacement.onopen({type: 'open'});
      assert.deepEqual(replacement.messages, [{type: 'viewer_auth', access: 'synthetic-replacement-token'}]);
      h.emitLocation(replacement);
      assertReset(h);
      h.emit(replacement, {type: 'auth_ok', role: 'viewer'});
      h.emitLocation(replacement);
      assertStatus(h, 'live', 'Live driver location');
    });
  });

  test(`${kind}: synchronous transport failures leave a recoverable state without leaking timers`, () => {
    for (const transportFailure of ['construct', 'send']) {
      withHarness(kind, 'https://staging.example.invalid/api', {transportFailure}, h => {
        if (transportFailure === 'send') {
          h.sockets[0].onopen({type: 'open'});
          h.flush();
          assert.equal(h.sockets[0].closeCalls, 1);
          assertStatus(h, 'disconnected', 'Tracking disconnected. Reopen the trip to reconnect.');
        } else {
          assert.equal(h.sockets.length, 0);
          assertStatus(h, 'unavailable', 'Trip tracking is unavailable.');
        }
        assertReset(h);
        assert.equal(h.timerCount, 0);
      });
    }
  });

  test(`${kind}: an unacknowledged viewer handshake times out and ignores a late acknowledgement`, () => {
    withHarness(kind, 'https://staging.example.invalid/api', {}, h => {
      const socket = h.sockets[0];
      socket.onopen({type: 'open'});
      h.advanceTime(14_999);
      assertStatus(h, 'connecting', 'Connecting to trip tracking…');
      h.advanceTime(1);
      assertStatus(h, 'unavailable', 'Trip tracking is unavailable.');
      assert.equal(socket.closeCalls, 1);
      assert.equal(h.timerCount, 0);
      h.emit(socket, {type: 'auth_ok', role: 'viewer'});
      h.emitLocation(socket);
      assertReset(h);
      assertStatus(h, 'unavailable', 'Trip tracking is unavailable.');
    });
  });
}

test('provider: the route is visible without a fabricated driver marker and status follows Arabic locale', () => {
  withHarness('provider', 'https://staging.example.invalid/api', {routePolyline: 'synthetic-route-a', locale: 'ar'}, h => {
    assert.equal(carMarkers(h).length, 0);
    assert.equal(elements(h.output, node => node.type === 'Polyline').length, 1);
    assert.equal(elements(h.output, node => node.type === 'Marker').length, 2);
    assert.equal(statusMessage(h), 'جارٍ الاتصال بتتبع الرحلة…');
    assert.equal(elements(h.output, node => node.props?.role === 'status')[0].props.dir, 'rtl');
    h.authenticate();
    assert.equal(statusMessage(h), 'في انتظار موقع حديث للسائق…');
    h.emit(h.sockets[0], {type: 'ended', reason: 'completed'});
    assert.equal(statusMessage(h), 'اكتملت الرحلة. توقف التتبع.');
  });
});

console.log('Controlled effect simulation: real source, fake transport/Maps/clock/animation; no browser or connected acceptance.');
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
