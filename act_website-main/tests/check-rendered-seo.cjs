// Requests only the locally built server, without JS hydration or external APIs.
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-H', '127.0.0.1', '-p', '3001'], { stdio: 'inherit' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const airports = ['heathrow', 'gatwick', 'stansted', 'luton', 'london-city'];
async function page(path) {
  const response = await fetch('http://127.0.0.1:3001' + path, {redirect: 'manual', signal: AbortSignal.timeout(30000)});
  assert.equal(response.status, 200, `${path}: HTTP status`);
  return response.text();
}
async function main() {
  let ready = false;
  for (let i = 0; i < 45; i++) {
    if (server.exitCode !== null) throw Error('Next server stopped');
    try { await page('/en'); ready = true; break; } catch { await pause(1000); }
  }
  assert.ok(ready, 'Server ready within 45 attempts');
  const failures = [];
  let passed = 0;
  for (const locale of ['en', 'ar']) {
    for (const airport of [null, ...airports]) {
      const path = `/${locale}` + (airport ? `/${airport}-airport-transfer` : '');
      try {
        const html = await page(path);
        const tags = html.match(/<(?:link|meta)\b[^>]*>/g) || [];
        assert.ok(tags.some(t => t.includes('rel="canonical"') && t.includes(`href="https://airportandcitytransfer.com${path}"`)), `${path}: canonical`);
        for (const lang of ['en', 'ar', 'x-default']) assert.ok(tags.some(t => t.toLowerCase().includes(`hreflang="${lang}"`)), `${path}: alternate ${lang}`);
        if (!airport) {
          const title = (html.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || '';
          assert.ok(title.includes(locale === 'en' ? 'London Airport Transfers' : 'خدمات النقل من وإلى مطارات لندن'), `${path}: title`);
          assert.ok(tags.some(t => t.includes('name="description"') && t.includes(locale === 'en' ? 'Book private airport' : 'احجز خدمات النقل')), `${path}: description`);
        } else {
          // Match actual anchor elements, not strings embedded in RSC payloads.
          const anchors = html.match(/<a\b[^>]*>/g) || [];
          assert.ok(anchors.some(t => t.includes(`href="/${locale}#book-now"`)), `${path}: rendered booking anchor`);
          assert.ok(anchors.some(t => t.includes(`href="/${locale}/about-us#contact-us"`)), `${path}: rendered contact anchor`);
          const schemas = [...html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].map(m => JSON.parse(m[1]));
          assert.ok(schemas.some(s => s['@type'] === 'Service' && s.url === `https://airportandcitytransfer.com${path}`), `${path}: Service URL`);
        }
        passed++; console.log('PASS', path);
      } catch (error) { failures.push(error.message); console.log('FAIL', error.message); }
    }
  }
  console.log(JSON.stringify({passed, failed: failures.length, failures}));
  assert.equal(failures.length, 0, 'All 12 rendered route checks must pass');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(() => server.kill('SIGTERM'));
