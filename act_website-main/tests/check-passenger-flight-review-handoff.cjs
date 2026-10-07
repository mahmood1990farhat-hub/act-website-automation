const assert=require("node:assert/strict"),fs=require("node:fs");
const confirm=fs.readFileSync("src/components/_components/bookTaxi/ConfirmFlightDetails.tsx","utf8");
const passenger=fs.readFileSync("src/components/_components/bookTaxi/PassengerDetails.tsx","utf8");
const flight=fs.readFileSync("src/components/_components/bookTaxi/FlightDetails.tsx","utf8");
const index=fs.readFileSync("src/components/_components/bookTaxi/index.tsx","utf8");

assert.ok(confirm.includes("bodyData.stop_points = stop_points;"),"review/payment handoff must preserve ordered stops");
assert.ok(confirm.includes('customerText(locale, "Pickup Time")'),"pickup time must not be labelled ETA");
assert.ok(!confirm.includes('"vcyHjlwA'),"review map must not contain an unrelated hardcoded route");
assert.ok(confirm.includes('runtimeText(locale, "mapUnavailable")'),"review needs an honest map-unavailable state");
assert.ok(!confirm.includes('{texts.meetAndGreet}</span>'),"review must not claim unselected meet & greet is included");

assert.ok(passenger.includes("isValidPhoneNumber(internationalPhone)"),"passenger phone must be validated");
assert.ok(passenger.includes("emailLooksValid"),"passenger email must be validated before payment");
assert.ok(passenger.includes('maxLength={254}'),"email UI must align with backend guest limit");
assert.ok(passenger.includes('maxLength={32}'),"phone UI must align with backend guest limit");

assert.ok(flight.includes('landingTime: flightType === "arrival" ? flightDetails.landingTime : ""'),"switching to departure must clear stale landing time");
assert.ok(flight.includes('departureTime: flightType === "departure" ? flightDetails.departureTime : ""'),"switching to arrival must clear stale departure time");
assert.ok(index.includes('infantSeatOption: d.infants > 0 ? current.infantSeatOption : ""'),"removed infants must clear stale infant-seat choice");
assert.ok(index.includes('childSeatOption: d.children > 0 ? current.childSeatOption : ""'),"removed children must clear stale child-seat choice");

console.log("PASS passenger/flight/review handoff regression guard");

const ts = require('typescript');
const vm = require('node:vm');
const { isValidPhoneNumber } = require('react-phone-number-input');

// Execute the actual component callbacks, not a duplicate regex or validator.
// React state and the payment HTTP boundary are replaced; phone metadata is real.
function compileSubmit(sourceText, filename) {
  const source = ts.createSourceFile(filename, sourceText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const handlers = [];
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(source) === 'onSubmit' &&
        node.initializer && ts.isArrowFunction(node.initializer)) handlers.push(node.initializer);
    ts.forEachChild(node, visit);
  }
  visit(source);
  assert.equal(handlers.length, 1, filename + ' must have exactly one submission callback');
  const compiled = ts.transpileModule('(' + handlers[0].getText(source) + ')', {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.None },
  }).outputText;
  return new vm.Script(compiled, { filename });
}

const submitPassenger = compileSubmit(passenger, 'PassengerDetails.tsx');
const submitReview = compileSubmit(confirm, 'ConfirmFlightDetails.tsx');
assert.ok(passenger.includes('onClick={onSubmit}'), 'Continue must use the tested callback');
const contact = { fullName: '  Test Passenger  ', email: '  Passenger.Test+trip@example.com  ',
  countryCode: '+44 United Kingdom', mobileNumber: '7464940000' };

function validateContact(changes) {
  const state = { saved: null, saves: 0, advances: 0, error: 'uncleared', validated: [] };
  submitPassenger.runInNewContext({
    passengerDetails: { ...contact, ...changes },
    t: (text) => text,
    setValidationError: (error) => { state.error = error; },
    setPassengerDetails: (details) => { state.saved = details; state.saves += 1; },
    nextStep: () => { state.advances += 1; },
    isValidPhoneNumber: (phone) => {
      state.validated.push(phone);
      return isValidPhoneNumber(phone);
    },
  })();
  return state;
}

async function checkPaymentHandoff(details, token) {
  const requests = [];
  const result = {};
  await submitReview.runInNewContext({
    data: {
      routePoints: [
        { type: 'pickup', point: { coordinates: { lat: 51.47, lng: -0.4543 } } },
        { type: 'dropoff', point: { coordinates: { lat: 51.5074, lng: -0.1278 } } },
      ],
      date: '2030-01-01', time: '12:00', numberOfPassengers: 1,
      adults: 1, children: 0, infants: 0, smallSuitcase: 0, largeSuitcase: 0,
      cartype: 1, total_cost: 100, passengerDetails: details,
      flightDetails: {}, childInfantTravel: {}, additionalRequirements: {},
    },
    token, locale: 'en', console,
    runtimeText: (_locale, text) => text,
    setPaymentError: (error) => { result.error = error; },
    setIsLoading: (loading) => { result.loading = loading; },
    setClientSecret: (value) => { result.secret = value; },
    setPaymentTotal: (value) => { result.total = value; },
    setStep: (value) => { result.step = value; },
    postData: async (request) => {
      requests.push(request);
      return { client_secret: 'synthetic-not-a-stripe-secret', price_breakdown: { total_cost: 100 } };
    },
  })();
  assert.equal(requests.length, 1, 'review must initiate payment exactly once');
  assert.equal(requests[0].endpoint, token ? '/api/trips/initiate-payment/' : '/api/trips/initiate-guest-payment/');
  for (const [wire, field] of [['passenger_name', 'fullName'], ['passenger_email', 'email'],
    ['passenger_country_code', 'countryCode'], ['passenger_phone', 'mobileNumber']]) {
    assert.equal(requests[0].body[wire], details[field], 'payment must preserve ' + wire);
  }
  assert.equal(result.step, 8, 'successful payment initiation must reach the payment step');
  assert.equal(result.secret, 'synthetic-not-a-stripe-secret');
  assert.equal(result.total, 100);
  assert.equal(result.loading, false);
  assert.equal(result.error, '');
}

async function checkContactSubmission() {
  const valid = [
    ['+44 United Kingdom', '7464940000', '+447464940000'],
    ['+44 United Kingdom', '07464940000', '+447464940000'],
    ['+44 United Kingdom', ' 07464 940000 ', '+447464940000'],
    ['+44 United Kingdom', '(07464) 940-000', '+447464940000'],
    ['+44 United Kingdom', '+447464940000', '+447464940000'],
    ['+44 United Kingdom', '+44 7464 940000', '+447464940000'],
    ['+33 France', '0612345678', '+33612345678'],
    ['+1 United States', '2133734253', '+12133734253'],
  ];
  for (const [countryCode, mobileNumber, expectedPhone] of valid) {
    const state = validateContact({ countryCode, mobileNumber });
    assert.equal(state.error, '', 'valid contact must not display an error');
    assert.equal(state.advances, 1, 'valid contact must advance once');
    assert.equal(state.saves, 1, 'valid contact must be saved before advancing');
    assert.deepEqual(state.validated, [expectedPhone], 'validate the expected international number');
    assert.equal(state.saved.fullName, 'Test Passenger');
    assert.equal(state.saved.email, 'Passenger.Test+trip@example.com');
    assert.equal(state.saved.mobileNumber, mobileNumber.trim());
    await checkPaymentHandoff(state.saved, undefined);
    await checkPaymentHandoff(state.saved, 'synthetic-session-token');
  }
  const invalid = [
    { fullName: ' ' }, { email: '' }, { countryCode: '' }, { mobileNumber: ' ' },
    { email: 'not-an-email' }, { email: 'a@@example.com' }, { email: 'a b@example.com' },
    { mobileNumber: '123' }, { mobileNumber: 'abc' }, { mobileNumber: '0000000000' },
    { countryCode: 'United Kingdom' }, { mobileNumber: '++447464940000' },
  ];
  for (const fields of invalid) {
    const state = validateContact(fields);
    assert.ok(state.error && state.error !== 'uncleared', 'invalid contact must display an error');
    assert.equal(state.advances, 0, 'invalid contact must not advance');
    assert.equal(state.saves, 0, 'invalid contact must not be saved for payment');
  }
  console.log('PASS 8 valid and 12 invalid passenger submissions; 16 mocked guest/authenticated payment handoffs; real phone validator');
}
checkContactSubmission().catch((error) => { console.error(error); process.exitCode = 1; });
