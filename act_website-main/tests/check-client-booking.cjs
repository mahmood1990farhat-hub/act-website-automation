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
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
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
    assert.ok(await page.getByRole('heading',{name:'Heathrow Airport Transfer London',exact:true}).isVisible());
    const contact = page.locator(`a[href="/${locale}/about-us#contact-us"]`).first();
    await contact.click();
    await page.locator('#contact-us').waitFor({state:'visible'});
    await page.goto(`${origin}/${locale}`, {waitUntil:'networkidle'});
    const input = page.locator('input[placeholder="'+(locale === 'en'?'Search for a location in London...':'ابحث عن موقع في لندن...')+'"]').first();
    await input.waitFor({state:'visible'});
    await input.fill('Synthetic London');
    const selected = page.getByText('Synthetic Test Street, London, UK',{exact:true}).first();
    await selected.waitFor({state:'visible'});
    const response = page.waitForResponse(r=>r.url().includes('/api/place-details'));
    await selected.click();
    await response;
    assert.equal(await input.inputValue(),'Synthetic Test Street, London, UK');
    console.log('PASS client content/contact/location selection',locale);
  }
  assert.equal(details,2,'Two simulated location-detail responses');
  assert.deepEqual(errors,[],'No uncaught browser errors');
  console.log('PASS bounded client acceptance; no quote, booking or payment submitted');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
