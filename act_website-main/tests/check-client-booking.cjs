// Bounded local-app test, no live services, credentials, booking or payment.
const { chromium } = require('/opt/browser-test/node_modules/playwright');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const origin = 'http://127.0.0.1:3001';
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-H', '127.0.0.1', '-p', '3001'], {stdio: 'inherit'});
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
  let writeRequests = 0;
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname === 'maps.googleapis.com') mapsRequests++;
    if (route.request().method() !== 'GET') writeRequests++;
    if (url.origin !== origin) return route.abort();
    if (url.pathname === '/api/places') return route.fulfill({json: {status:'OK', predictions:[{description:'Synthetic Test Street, London, UK', place_id:'synthetic-only', reference:'synthetic-only', matched_substrings:[]}]}});
    if (url.pathname === '/api/place-details') {
      details++;
      return route.fulfill({json: {result:{geometry:{location:{lat:51.5074,lng:-0.1278}}}}});
    }
    if (url.pathname.startsWith('/api/') || route.request().method() !== 'GET') return route.abort();
    return route.continue();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  for (const locale of ['en','ar']) {
    await page.goto(`${origin}/${locale}/heathrow-airport-transfer`, {waitUntil:'networkidle'});
    assert.ok(await page.getByRole('heading',{name:locale === 'ar' ? 'خدمة التوصيل من وإلى مطار هيثرو في لندن' : 'Heathrow Airport Transfer London',exact:true}).isVisible());
    const contact = page.locator(`a[href="/${locale}/about-us#contact-us"]`).first();
    await contact.click();
    await page.locator('#contact-us').waitFor({state:'visible'});
    await page.goto(`${origin}/${locale}/heathrow-airport-transfer`, {waitUntil:'networkidle'});
    await page.locator(`a[href="/${locale}#book-now"]`).first().click();
    await page.locator('#book-now').waitFor({state:'visible'});
    for (const placeholder of (locale === 'en'
      ? ['Search for a location in London...', 'Search for a location in the UK...']
      : ['ابحث عن موقع في لندن...', 'ابحث عن موقع في المملكة المتحدة...'])) {
    const input = page.getByPlaceholder(placeholder, {exact:true});
    await input.waitFor({state:'visible'});
    await input.fill('Synthetic London');
    const selected = page.getByText('Synthetic Test Street, London, UK',{exact:true}).first();
    await selected.waitFor({state:'visible'});
    const response = page.waitForResponse(r=>r.url().includes('/api/place-details'));
    await selected.click();
    await response;
    assert.equal(await input.inputValue(),'Synthetic Test Street, London, UK');
    }
    assert.equal(await page.evaluate(() => typeof window.google), 'undefined', 'No Maps browser global needed');
    console.log('PASS content/contact/booking link/pickup/dropoff with Maps unavailable',locale);
  }
  assert.equal(details,4,'Four simulated location-detail responses');
  assert.equal(mapsRequests,0,'Public pages do not request the Maps browser SDK');
  assert.equal(writeRequests,0,'No quote, booking or payment writes attempted');
  // This is a Maps-independent booking-entry check, NOT payment acceptance.
  // Keep the known offline Stripe error visible; all other page errors fail.
  const offlineStripeErrors = errors.filter(e => e === 'Failed to load Stripe.js');
  console.log('KNOWN OFFLINE STRIPE ERRORS (payment unverified):', offlineStripeErrors.length);
  assert.deepEqual(errors.filter(e => e !== 'Failed to load Stripe.js'),[], 'No unexpected browser errors');
  console.log('PASS focused booking-entry scope only; real Maps/Places/quote/payment remain unverified');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
