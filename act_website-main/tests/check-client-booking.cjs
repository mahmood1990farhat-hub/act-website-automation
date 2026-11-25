// Bounded local-app test, no live services, credentials, booking or payment.
const { chromium } = require('/opt/browser-test/node_modules/playwright');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const origin = 'http://127.0.0.1:3001';
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-H', '127.0.0.1', '-p', '3001'], {stdio: 'inherit'});
const places = [
  {id: 'synthetic-pickup', description: 'Synthetic Pickup Street, London, UK', coordinates: {lat: 51.5074, lng: -0.1278}},
  {id: 'synthetic-dropoff', description: 'Synthetic Dropoff Street, London, UK', coordinates: {lat: 51.5140, lng: -0.1310}},
];
const previewPath = '/api/trips/route-preview/';
const cors = {
  'Access-Control-Allow-Origin': origin,
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
let browser;
async function main() {
  let ready = false;
  for (let i = 0; i < 45; i++) {
    try { if ((await fetch(origin + '/en')).ok) {ready = true; break;} } catch {}
    await new Promise(r => setTimeout(r, 1000));
  }
  assert.ok(ready, 'Local server ready');
  browser = await chromium.launch({headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']});
  const context = await browser.newContext({serviceWorkers: 'block'});
  const errors = [];
  let details = 0;
  let mapsRequests = 0;
  const previewBodies = [];
  const unexpectedWrites = [];
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname === 'maps.googleapis.com' && url.pathname === '/maps/api/js') {
      mapsRequests++;
      return route.abort();
    }
    if (url.pathname === previewPath && request.method() === 'OPTIONS') {
      return route.fulfill({status: 204, headers: cors});
    }
    if (url.pathname === previewPath && request.method() === 'POST') {
      previewBodies.push(request.postDataJSON());
      return route.fulfill({headers: cors, json: {
        route_polyline: 'g`kyHv}W{OnFkWnK', route_proof: 'synthetic-preview-only',
      }});
    }
    if (request.method() !== 'GET' && request.method() !== 'OPTIONS') {
      unexpectedWrites.push(url.pathname);
      return route.abort();
    }
    if (url.origin !== origin) return route.abort();
    if (url.pathname === '/api/places') {
      const place = url.searchParams.get('input')?.includes('Dropoff') ? places[1] : places[0];
      return route.fulfill({json: {status:'OK', predictions:[{description: place.description,
        place_id: place.id, reference: place.id, matched_substrings:[]}
      ]}});
    }
    if (url.pathname === '/api/place-details') {
      const place = places.find(p => p.id === url.searchParams.get('place_id'));
      if (!place) return route.fulfill({status: 400, json: {}});
      details++;
      return route.fulfill({json: {result:{geometry:{location:place.coordinates}}}});
    }
    if (url.pathname.startsWith('/api/') || request.method() !== 'GET') return route.abort();
    return route.continue();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  for (const locale of ['en','ar']) {
    const beforeMaps = mapsRequests;
    const beforePreview = previewBodies.length;
    await page.setViewportSize({width:1440, height:920});
    await page.goto(`${origin}/${locale}/heathrow-airport-transfer`, {waitUntil:'networkidle'});
    assert.ok(await page.getByRole('heading',{name:locale === 'ar' ? 'خدمة التوصيل من وإلى مطار هيثرو في لندن' : 'Heathrow Airport Transfer London',exact:true}).isVisible());
    const contact = page.locator(`a[href="/${locale}/about-us#contact-us"]`).first();
    await contact.click();
    await page.locator('#contact-us').waitFor({state:'visible'});
    await page.goto(`${origin}/${locale}/heathrow-airport-transfer`, {waitUntil:'networkidle'});
    await page.locator(`a[href="/${locale}#book-now"]`).first().click();
    await page.locator('#book-now').waitFor({state:'visible'});
    if (locale === 'ar') await page.setViewportSize({width:390, height:844});
    const placeholders = locale === 'en'
      ? ['Search for a location in London...', 'Search for a location in the UK...']
      : ['ابحث عن موقع في لندن...', 'ابحث عن موقع في المملكة المتحدة...'];
    for (const [index, placeholder] of placeholders.entries()) {
      const place = places[index];
      const input = page.getByPlaceholder(placeholder, {exact:true});
      await input.fill(index === 0 ? 'Synthetic Pickup' : 'Synthetic Dropoff');
      const selected = page.getByText(place.description,{exact:true}).first();
      await selected.waitFor({state:'visible'});
      assert.equal(previewBodies.length, beforePreview, 'Typing or one selected endpoint does not request driving directions');
      assert.equal(mapsRequests, beforeMaps, 'Do not load Maps before both locations resolve');
      const response = page.waitForResponse(r=>r.url().includes('/api/place-details'));
      const preview = index === 1 ? page.waitForResponse(r =>
        new URL(r.url()).pathname === previewPath && r.request().method() === 'POST') : undefined;
      await selected.click();
      await Promise.all([response, preview]);
      assert.equal(await input.inputValue(), place.description);
    }
    const fallback = locale === 'ar' ? 'الخريطة غير متاحة. تفاصيل المسار موضحة أعلاه.' : 'Map unavailable. Your route details are shown above.';
    await page.getByText(fallback, {exact:true}).filter({visible:true}).first().waitFor({state:'visible'});
    await page.waitForLoadState('networkidle');
    assert.ok(mapsRequests > beforeMaps, 'Two resolved addresses mount the map before date, time or price');
    assert.equal(previewBodies.length, beforePreview + 1, 'One preview per completed address pair');
    const body = previewBodies[beforePreview];
    assert.deepEqual(body.pickup_location, places[0].coordinates);
    assert.deepEqual(body.dropoff_location, places[1].coordinates);
    assert.deepEqual(body.stop_points ?? [], []);
    assert.equal(body.trip_date, undefined);
    assert.equal(body.trip_time, undefined);
    assert.equal(await page.evaluate(() => typeof window.google?.maps?.Map), 'undefined', 'Real Maps disabled in this test');
    console.log('PASS content/contact/booking links, selected addresses and pre-price map fallback', locale);
  }
  assert.equal(details, 4, 'Four simulated location-detail responses');
  assert.deepEqual(unexpectedWrites, [], 'Opening the route preview does not submit a quote, booking or payment');
  // Keep the known offline Stripe error visible; all other page errors fail.
  const offlineStripeErrors = errors.filter(e => e === 'Failed to load Stripe.js');
  console.log('KNOWN OFFLINE STRIPE ERRORS (payment unverified):', offlineStripeErrors.length);
  assert.deepEqual(errors.filter(e => e !== 'Failed to load Stripe.js'),[], 'No unexpected browser errors');
  console.log('PASS focused booking-entry scope only; real Maps/Places/quote/payment remain unverified');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
