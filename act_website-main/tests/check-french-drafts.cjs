// Offline content checks. Does not enable French, call APIs or submit bookings.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const json = p => JSON.parse(read(p));
const excludedAuth = ['CreateCaptainAccount', 'driverOnboarding', 'GetStartedCaptain', 'admin_login'];
const flatten = (value, prefix = '', result = {}) => {
  if (value !== null && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) flatten(child, prefix ? `${prefix}.${key}` : key, result);
  } else result[prefix] = value;
  return result;
};
const tokens = value => [...value.matchAll(/\{[a-zA-Z][a-zA-Z0-9_]*\}/g)].map(x => x[0]).sort();
const summary = {};
const unchanged = {};
for (const section of ['home', 'auth', 'complaints', 'lostProperty', 'tripsPassenger']) {
  const en = json(`src/dictionaries/en/${section}.json`);
  const fr = json(`src/dictionaries/fr/${section}.json`);
  if (section === 'auth') {
    for (const key of excludedAuth) {
      assert.ok(Object.hasOwn(en, key), `Stale auth exclusion: ${key}`);
      delete en[key];
      assert.ok(!Object.hasOwn(fr, key), `Driver/admin text must remain out of scope: ${key}`);
    }
  }
  function shape(a, b, location) {
    assert.equal(Array.isArray(b), Array.isArray(a), `${location}: array shape`);
    if (a !== null && typeof a === 'object') {
      assert.ok(b !== null && typeof b === 'object', location);
      assert.deepEqual(Object.keys(b).sort(), Object.keys(a).sort(), `${location}: exact keys/array length`);
      for (const key of Object.keys(a)) shape(a[key], b[key], `${location}.${key}`);
    } else {
      assert.equal(typeof b, typeof a, `${location}: value type`);
      if (typeof a === 'string') {
        if (a.trim()) assert.ok(b.trim(), `${location}: blank translation`);
        assert.deepEqual(tokens(b), tokens(a), `${location}: interpolation placeholders`);
      } else assert.deepEqual(b, a, `${location}: non-text data changed`);
    }
  }
  shape(en, fr, section);
  const e = flatten(en), f = flatten(fr);
  unchanged[section] = [];
  for (const [key, value] of Object.entries(e)) {
    if (typeof value !== 'string') continue;
    if (/\.(value|downloadFileName)$/.test(key) || section === 'tripsPassenger' && key === 'tripCard.gbp') {
      assert.equal(f[key], value, `${section}.${key}: machine value changed`);
    }
    if (section === 'home' && /\.(url|href)$/.test(key)) {
      const target = value.startsWith('/en') ? value.replace(/^\/en(?=\/|#|$)/, '/fr') : `/fr${value}`;
      assert.equal(f[key], target, `${key}: route/anchor changed`);
    }
    if (f[key] === value) unchanged[section].push(key);
  }
  summary[section] = Object.values(f).filter(v => typeof v === 'string').length;
}
const enHome = json('src/dictionaries/en/home.json'), frHome = json('src/dictionaries/fr/home.json');
assert.deepEqual(frHome.footer.Call_us.phone_numbers.Elements, enHome.footer.Call_us.phone_numbers.Elements);
assert.deepEqual(frHome.footer.Call_us.Email_us.Elements, enHome.footer.Call_us.Email_us.Elements);
assert.deepEqual(frHome.footer.location.Elements, enHome.footer.location.Elements);
assert.equal(frHome.home.Booking_Confirmation.desc.hour.trim(), '2', 'Approved master: driver details about two hours before journey');
assert.ok(frHome.home.Booking_Confirmation.desc.span_2.includes('avant votre trajet'));
assert.equal(frHome.home.Booking_Confirmation.desc.hour_5, enHome.home.Booking_Confirmation.desc.hour_5);
assert.equal(frHome.home.Confir_flight_details.vat_20, 'Majoration commerciale (20 %)');
const airports = json('src/dictionaries/fr/airports.json');
const airportSlugs = ['heathrow', 'gatwick', 'stansted', 'luton', 'london-city'].map(x => `${x}-airport-transfer`);
assert.deepEqual(Object.keys(airports.pages).sort(), airportSlugs.sort());
for (const [slug, page] of Object.entries(airports.pages)) {
  assert.equal(page.routes.length, 6, `${slug}: routes`);
  assert.ok(page.heading && page.metadata.title && page.metadata.description, `${slug}: metadata`);
  for (const value of Object.values(flatten(airports.shared))) {
    assert.equal(typeof value, 'string');
    assert.ok(value.trim());
    assert.deepEqual(tokens(value.replaceAll('{airport}', page.airport)), [], `${slug}: unhandled airport token`);
  }
}
assert.equal(airports.shared.faqs.length, 4);
assert.ok(airports.pages['london-city-airport-transfer'].vehicleFaq.a.includes('berline affaires'));
const supplement = json('src/dictionaries/fr/bookingSupplement.json');
assert.deepEqual(tokens(supplement.flight.departureGuidance), ['{windowEnd}', '{windowStart}']);
assert.deepEqual(tokens(supplement.flight.arrivalGuidance), ['{suggestedPickup}']);
assert.equal(supplement.childSeats.infantOptions.length, 3);
assert.equal(supplement.childSeats.childOptions.length, 3);
assert.equal(Object.keys(supplement.passenger.countryLabels).length, 8);
assert.ok(supplement.languageNotices.booking.includes('GBP'));
assert.match(read('i18n.config.ts'), /fr:\s*\{[^}]*enabled:\s*false/);
assert.ok(read('src/lib/translation.ts').includes('dictionaries/fr/'), 'French drafts wired for isolated preview; publication still disabled');
assert.match(read('src/middleware.ts'), /isSupportedLocale/);
assert.match(read('src/middleware.ts'), /noindex/);
console.log(JSON.stringify({status: 'PASS', stringValuesBySection: summary, airportPages: 5, authExclusions: excludedAuth, unchangedStringsForHumanReview: unchanged, scope: 'Content structure, tokens, route targets, protected values and source-level hidden-state checks only; not a UI, legal or live-payment acceptance test.'}, null, 2));
