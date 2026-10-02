// Offline display regression checks. No network, bookings, payments or emails.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const resolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...args) {
  return resolve.call(this, request.startsWith('@/') ? path.join(root, 'src', request.slice(2)) : request, ...args);
};
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, file) => {
  module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    fileName: file,
  }).outputText, file);
};
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const base = path.join(root, 'src/components/_components/bookTaxi');
const { bookingText } = require(path.join(base, 'booking-text.ts'));
const guidance = require(path.join(base, 'flight-guidance.ts'));
const noop = () => {};
const render = (name, locale, props) => renderToStaticMarkup(React.createElement(require(path.join(base, name + '.tsx')).default, { locale, nextStep: noop, prevStep: noop, ...props }));
const passenger = { passengerDetails: { fullName: 'Test Passenger', email: 'test@example.invalid', countryCode: '+44 United Kingdom', mobileNumber: '7700900000' }, setPassengerDetails: noop };
const seats = { passengerCounts: { adults: 1, children: 1, infants: 1 }, childInfantTravel: { infantSeatOption: 'I will provide my own infant seats', childSeatOption: 'I would like ACT to provide child seats' }, setChildInfantTravel: noop };
const flight = { flightDetails: { flightType: 'arrival', flightNumber: 'BA123', airline: 'British Airways', landingTime: '10:00', departureTime: '', pickupSignName: 'Test Passenger' }, setFlightDetails: noop, pickupTime: '10:30', routePoints: [{ type: 'pickup', point: { airport_code: 'LHR' } }], changePickupTime: noop };
for (const [name, props, english, arabic] of [
  ['PassengerDetails', passenger, 'Passenger Details', 'بيانات الراكب'],
  ['ChildInfantTravelInfo', seats, 'Infant Seat Requirement', 'متطلبات مقعد الرضيع'],
  ['FlightDetails', flight, 'Flight Details', 'تفاصيل الرحلة الجوية'],
]) {
  const en = render(name, 'en', props), ar = render(name, 'ar', props);
  assert(en.includes(english)); assert(ar.includes(arabic));
  assert(ar.includes('dir="rtl"')); assert(!ar.includes('>' + english + '<'));
  if (name === 'PassengerDetails') { assert(ar.includes('value="+44 United Kingdom"')); assert(ar.includes('test@example.invalid')); }
  if (name === 'ChildInfantTravelInfo') { assert(ar.includes('value="I will provide my own infant seats"')); assert(ar.includes('سأوفّر مقاعد الرُضّع بنفسي')); }
}
assert.equal(bookingText('en', 'Continue'), 'Continue');
assert.equal(bookingText('ar', 'Unmodified customer input'), 'Unmodified customer input');
assert.equal(guidance.getArrivalGuidance('11:00', '10:00', 'ar'), '');
assert.equal(guidance.getDepartureGuidance('10:00', '12:00', 'ar'), '');
assert(guidance.getArrivalGuidance('10:30', '10:00', 'ar').includes('11:00 صباحًا'));
assert(guidance.getDepartureGuidance('11:30', '12:00', 'ar').includes('9:00 صباحًا'));
assert(guidance.getArrivalGuidance('23:30', '23:00', 'ar').includes('12:00 صباحًا'));
assert.equal(guidance.parseTimeToMinutes('24:00'), undefined);
assert.equal(guidance.getArrivalGuidance('bad', '10:00', 'ar'), '');
for (const name of ['PassengerDetails', 'ChildInfantTravelInfo', 'FlightDetails', 'RoutePoints', 'ConfirmFlightDetails', 'ChooseCar', 'BookingConfirmation']) {
  const file = path.join(base, name + '.tsx');
  const ast = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  function visit(node) { if (ts.isJsxText(node)) assert(!/[A-Za-z]{3}/.test(node.text.trim()), name + ': untranslated JSX: ' + node.text.trim()); ts.forEachChild(node, visit); }
  visit(ast);
}
console.log('PASS: EN/AR component rendering, RTL, canonical values, flight timing boundaries and booking-screen literal scan.');
