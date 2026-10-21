/* Isolated real-browser tests of the actual shared form. No ACT service calls.
 * Requires the frontend's locked dependencies and test-only playwright/esbuild.
 * Run: NODE_PATH=/tmp/act-ui-tools/node_modules node tests/driver-form-ui/run.cjs
 */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const { build } = require('esbuild');
const { chromium, webkit, devices } = require('playwright');
const postcss = require('postcss');
const tailwind = require('@tailwindcss/postcss');
const root = path.resolve(__dirname, '../..');
const out = path.join(root, '.driver-form-ui-test');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII=', 'base64');
const identity = ['pco_front', 'pco_back', 'dvla_front', 'dvla_back', 'driver_photo'];
const carDocs = ['mot', 'insurance', 'vehicle_phv', 'v5c'];
const file = (name='synthetic-document.png', mimeType='image/png', buffer=png) => ({name, mimeType, buffer});
const input = (page, name) => page.locator(`[data-document="${name}"] input[type=file]`);
const card = (page, name) => page.locator(`[data-document="${name}"]`);
const next = page => page.getByRole('button', {name:'Continue', exact:true}).click();
const back = page => page.getByRole('button', {name:'Back', exact:true}).click();
const message = async (page, text) => {
  await page.getByText(text, {exact:false}).first().waitFor({state:'visible'});
};
async function personal(page) {
  for (const [label, value] of [['First name','Synthetic'],['Last name','Applicant'],
    ['Date of birth (21+)','1990-01-01'],['UK mobile (+44)','+447700900123'],
    ['Email','driver-test@example.invalid'],['Postcode','SW1A 1AA'],['Current UK address','1 Synthetic Test Road']]) {
    await page.getByLabel(`${label} *`,{exact:true}).fill(value);
  }
}
async function driver(page, withFiles=true) {
  await personal(page); await next(page);
  await page.getByLabel('TfL PHV driver badge number *',{exact:true}).fill('SYNTHETIC-NOT-A-LICENCE');
  await page.getByLabel('TfL badge expiry *',{exact:true}).fill('2099-01-01');
  await page.getByLabel('Years of driving experience *',{exact:true}).selectOption('1_to_3');
  if(withFiles) for (const name of identity) await input(page,name).setInputFiles(file(`${name}.png`));
}
async function vehicle(page, ownership='phv_owner', withFiles=true) {
  await next(page);
  await page.getByLabel('Vehicle ownership *',{exact:true}).selectOption(ownership);
  if(ownership==='do_not_have_a_phv') return;
  await page.getByLabel('Vehicle make *',{exact:true}).selectOption('Toyota');
  await page.getByLabel('Vehicle model *',{exact:true}).selectOption('Prius');
  await page.getByLabel('Vehicle year (2015–present) *',{exact:true}).selectOption('2018');
  await page.getByLabel('ACT vehicle class *',{exact:true}).selectOption('comfort');
  for (const [label,value] of [['Vehicle registration (VRM)','TEST-ONLY'],['Vehicle colour','Black'],['MOT expiry','2099-01-01'],['Insurance expiry','2099-01-01']]) {
    await page.getByLabel(`${label} *`,{exact:true}).fill(value);
  }
  await page.getByLabel('Accepts pets? *',{exact:true}).selectOption('true');
  if(withFiles) for(const name of ['mot','insurance','vehicle_phv',ownership==='phv_owner'?'v5c':'hire_agreement']) await input(page,name).setInputFiles(file(`${name}.png`));
}
async function consents(page) {
  for(const box of await page.locator('input[type=checkbox]').all()) await box.check();
}
async function submitted(page) {
  await page.getByRole('button',{name:'Submit application',exact:true}).click();
  await message(page,'Application received');
  return page.evaluate(()=>window.__submissions);
}
const tests = [
  ['missing document errors revalidate immediately without extra submit', async page => {
    await driver(page,false); await next(page);
    await message(page,'Select your TfL PHV badge — front.');
    for(const name of identity) await input(page,name).setInputFiles(file(`${name}.png`));
    assert.equal(await page.getByRole('alert').count(),0);
    await next(page); await page.getByLabel('Vehicle ownership *',{exact:true}).waitFor();
    assert.equal(await page.evaluate(()=>window.__submissions.length),0);
  }],
  ['upload opens picker; selection is single; cancel, replace, remove and same-file reselect', async page => {
    await driver(page,false);
    const chooser = page.waitForEvent('filechooser');
    await card(page,'pco_front').getByRole('button',{name:/Upload your document/}).click();
    await (await chooser).setFiles(file('first.png'));
    assert.equal(await card(page,'pco_front').getByText('first.png',{exact:true}).count(),1);
    await input(page,'pco_front').setInputFiles([]); // Simulate empty/cancel result; retain parent File.
    await message(page,'first.png');
    await input(page,'pco_front').setInputFiles(file('first.png'));
    await input(page,'pco_front').setInputFiles(file('replacement.png'));
    assert.equal(await card(page,'pco_front').getByText('first.png',{exact:true}).count(),0);
    await card(page,'pco_front').getByRole('button',{name:/Remove/}).click();
    await message(page,'No document selected.');
    assert.equal(await card(page,'pco_front').locator('[data-selected-filename]').count(),0);
    await input(page,'pco_front').setInputFiles(file('replacement.png'));
    await message(page,'Selected — ready to submit. Not uploaded yet.');
  }],
  ['empty, oversized and unsupported evidence rejected; PDF driver photo rejected', async page => {
    await driver(page);
    for(const [f, text] of [[file('empty.png','image/png',Buffer.alloc(0)),'This file is empty.'],
      [file('huge.png','image/png',Buffer.alloc(10*1024*1024+1)), 'no larger than 10 MB'],
      [file('wrong.txt','text/plain',Buffer.from('synthetic')),'Choose a PDF, JPG or PNG document.']]) {
      await input(page,'pco_front').setInputFiles(f); await message(page,text); await next(page);
      assert.equal(await page.getByLabel('Vehicle ownership *',{exact:true}).count(),0);
    }
    await input(page,'pco_front').setInputFiles(file('pco_front.png'));
    await input(page,'driver_photo').setInputFiles(file('photo.pdf','application/pdf',Buffer.from('%PDF-synthetic')));
    await message(page,'Choose a JPG or PNG photograph.'); await next(page);
    assert.equal(await page.getByLabel('Vehicle ownership *',{exact:true}).count(),0);
    await input(page,'driver_photo').setInputFiles(file('driver_photo.png')); await next(page);
    await page.getByLabel('Vehicle ownership *',{exact:true}).waitFor();
  }],
  ['Back/Continue retains exact files and final multipart uses the same state', async page => {
    await driver(page); await vehicle(page);
    await back(page); for(const name of identity) await message(page,`${name}.png`);
    await next(page); for(const name of carDocs) {
      assert.equal(await card(page,name).getByText(`${name}.png`,{exact:true}).count(),1);
      assert.equal(await input(page,name).isVisible(),false);
    }
    await next(page); await message(page,'Review your application before submitting.');
    assert.equal(await page.evaluate(()=>window.__submissions.length),0);
    await consents(page); const rows=await submitted(page);
    assert.equal(rows.length,1);
    for(const name of [...identity,...carDocs]) assert.equal(rows[0][name].name,`${name}.png`);
    assert.equal(rows[0].vehicle_make,'Toyota'); assert.equal(rows[0].vehicle_model,'Prius');
  }],
  ['make/model dependency, year range and not-listed fallback', async page => {
    await driver(page); await vehicle(page);
    await page.getByLabel('Vehicle make *',{exact:true}).selectOption('BMW');
    assert.equal(await page.getByLabel('Vehicle model *',{exact:true}).inputValue(),'');
    assert.equal(await page.getByLabel('Vehicle model *',{exact:true}).getByRole('option',{name:'Prius',exact:true}).count(),0);
    const years=await page.getByLabel('Vehicle year (2015–present) *',{exact:true}).locator('option').evaluateAll(xs=>xs.map(x=>x.value).filter(Boolean));
    const year=await page.evaluate(()=>new Date().getFullYear());
    assert.equal(years[0],String(year)); assert.equal(years.at(-1),'2015'); assert.equal(years.length,year-2014);
    await page.getByLabel('Vehicle model *',{exact:true}).selectOption('__other__');
    await page.getByLabel('Enter vehicle model *',{exact:true}).fill('Unlisted model');
    await back(page); await next(page);
    assert.equal(await page.getByLabel('Enter vehicle model *',{exact:true}).inputValue(),'Unlisted model');
    await page.getByLabel('Vehicle make *',{exact:true}).selectOption('__other__');
    await page.getByLabel('Enter vehicle make *',{exact:true}).fill('Unlisted make');
    await page.getByLabel('Enter vehicle model *',{exact:true}).fill('Unlisted model');
    await next(page); await consents(page); const rows=await submitted(page);
    assert.equal(rows[0].vehicle_make,'Unlisted make'); assert.equal(rows[0].vehicle_model,'Unlisted model');
    assert.equal(JSON.stringify(rows).includes('__other__'),false);
  }],
  ['rental path uses hire agreement, not hidden owner evidence', async page => {
    await driver(page); await vehicle(page);
    await page.getByLabel('Vehicle ownership *',{exact:true}).selectOption('hiring_a_phv');
    assert.equal(await card(page,'v5c').count(),0); await next(page);
    await message(page,'Select your rental / hire / lease agreement.');
    await input(page,'hire_agreement').setInputFiles(file('hire-agreement.png'));
    assert.equal(await page.getByRole('alert').count(),0);
    await next(page); await consents(page); const rows=await submitted(page);
    assert.equal(rows[0].vehicle_ownership,'hiring_a_phv'); assert.equal(rows[0].hire_agreement.name,'hire-agreement.png');
    assert.equal('v5c' in rows[0],false);
  }],
  ['no-vehicle application excludes retained vehicle details and files', async page => {
    await driver(page); await vehicle(page);
    await input(page,'v5c').setInputFiles(file('bad.txt','text/plain',Buffer.from('invalid')));
    await page.getByLabel('Vehicle ownership *',{exact:true}).selectOption('do_not_have_a_phv');
    await next(page); await consents(page); const rows=await submitted(page);
    for(const key of ['vehicle_make','vehicle_model','vehicle_year',...carDocs]) assert.equal(key in rows[0],false);
    assert.equal(rows[0].vehicle_ownership,'do_not_have_a_phv');
    for(const name of identity) assert.equal(rows[0][name].name,`${name}.png`);
  }],
  ['consent warning clears only when complete; final click sends once', async page => {
    await driver(page); await vehicle(page,'do_not_have_a_phv'); await next(page);
    await page.getByRole('button',{name:'Submit application',exact:true}).click();
    await message(page,'You must agree to the ACT policies and DBS verification requirement.');
    const boxes=page.locator('input[type=checkbox]'); await boxes.nth(0).check(); await boxes.nth(1).check();
    assert.equal(await page.getByRole('alert').count(),1);
    await boxes.nth(2).check(); assert.equal(await page.getByRole('alert').count(),0);
    assert.equal(await page.evaluate(()=>window.__submissions.length),0);
    await page.getByRole('button',{name:'Submit application',exact:true}).evaluate(button=>{button.click();button.click();});
    await message(page,'Application received'); assert.equal(await page.evaluate(()=>window.__submissions.length),1);
  }],
  ['implicit form submission advances an early step without posting', async page => {
    await personal(page); await page.locator('form').evaluate(form=>form.requestSubmit());
    await page.getByLabel('TfL PHV driver badge number *',{exact:true}).waitFor();
    assert.equal(await page.evaluate(()=>window.__submissions.length),0);
    // Browser-generated form submission without the final submit button is ignored at review.
    await page.getByLabel('TfL PHV driver badge number *',{exact:true}).fill('SYNTHETIC');
    await page.getByLabel('TfL badge expiry *',{exact:true}).fill('2099-01-01');
    await page.getByLabel('Years of driving experience *',{exact:true}).selectOption('1_to_3');
    for(const name of identity) await input(page,name).setInputFiles(file(`${name}.png`));
    await vehicle(page,'do_not_have_a_phv'); await next(page); await consents(page);
    await page.locator('form').evaluate(form=>form.requestSubmit());
    assert.equal(await page.evaluate(()=>window.__submissions.length),0);
  }],
  ['layout, long filenames, visible controls and pending-state preservation', async (page, tag) => {
    await driver(page); await input(page,'pco_front').setInputFiles(file('synthetic_'+'long_document_'.repeat(14)+'.png'));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
    for(const button of await card(page,'pco_front').getByRole('button').all()) {
      const box=await button.boundingBox(); assert.ok(box&&box.height>=44);
    }
    await page.screenshot({path:path.join(out,`${tag}-identity.png`),fullPage:true});
    await vehicle(page); await page.screenshot({path:path.join(out,`${tag}-vehicle.png`),fullPage:true});
    await next(page); await page.screenshot({path:path.join(out,`${tag}-review.png`),fullPage:true});
    await consents(page); await submitted(page);
    await message(page,'pending verification');
  }],
];

(async()=>{
  await fs.mkdir(out,{recursive:true});
  await build({stdin:{contents:'import React from "react"; import {createRoot} from "react-dom/client"; import Form from "./src/components/_components/auth/captain/UnifiedDriverApplication"; createRoot(document.getElementById("root")).render(<Form locale="en"/>);',resolveDir:root,loader:'tsx'},
    bundle:true,jsx:'automatic',outfile:path.join(out,'app.js'),define:{'process.env.NEXT_PUBLIC_API_BASE_URL':'""','process.env.NODE_ENV':'"test"'}});
  const css=await postcss([tailwind({base:root})]).process('@import "tailwindcss"; @source "../../src/components/_components/auth/captain";',{from:path.join(__dirname,'fixture.css')});
  await fs.writeFile(path.join(out,'app.css'),css.css);
  await fs.writeFile(path.join(out,'index.html'),'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/app.css"><title>ACT isolated form review</title><style>body{margin:0;padding:16px;font-family:Arial,sans-serif;background:#101624}*{box-sizing:border-box}</style></head><body><div id="root"></div><script src="/app.js"></script></body></html>');
  const server=http.createServer(async(req,res)=>{
    const routes={'/':'index.html','/app.js':'app.js','/app.css':'app.css'};
    const f=routes[new URL(req.url,'http://127.0.0.1').pathname];
    if(!f){res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type',f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':'text/html');
    res.end(await fs.readFile(path.join(out,f)));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url=`http://127.0.0.1:${server.address().port}/`;
  let passed=0;
  try {
    for(const [tag,engine,opts] of [['desktop-chromium',chromium,{viewport:{width:1440,height:1000}}],['mobile-webkit',webkit,{...devices['iPhone 13']}]]) {
      const browser=await engine.launch();
      try {
        for(const [name,run] of tests){
          const context=await browser.newContext({...opts,serviceWorkers:'block'});
          const forbidden=[];
          await context.route('**/*',route=>{
            const dest=new URL(route.request().url());
            if(dest.origin===new URL(url).origin) return route.continue();
            forbidden.push(dest.origin);return route.abort();
          });
          await context.addInitScript(()=>{
            window.__submissions=[];
            const original=window.fetch.bind(window);
            window.fetch=async(resource,init)=>{
              const u=new URL(String(resource),location.origin);
              if(u.pathname==='/api/places') return new Response(JSON.stringify({status:'ZERO_RESULTS',predictions:[]}),{status:200});
              if(u.pathname==='/api/drivers/onboarding/apply/') {
                if(!(init?.body instanceof FormData)) throw new Error('Expected multipart body');
                const row={};for(const [key,value] of init.body.entries()) row[key]=value instanceof File?{name:value.name,size:value.size,type:value.type}:value;
                window.__submissions.push(row);await new Promise(r=>setTimeout(r,80));
                return new Response(JSON.stringify({application_id:900001,status:'pending_verification'}),{status:201});
              }
              if(u.pathname.startsWith('/api/')) throw new Error('Unexpected API request');
              return original(resource,init);
            };
          });
          const page=await context.newPage();page.setDefaultTimeout(6000);
          const errors=[];page.on('pageerror',e=>errors.push(e.message));
          try {
            await page.goto(url);await run(page,tag);
            assert.deepEqual(forbidden,[]);assert.deepEqual(errors,[]);
            console.log(`PASS ${tag}: ${name}`);passed++;
          } catch(error) {
            await page.screenshot({path:path.join(out,`${tag}-failure.png`),fullPage:true}).catch(()=>{});
            throw new Error(`${tag}: ${name}: ${error.stack}`);
          } finally {await context.close();}
        }
      } finally {await browser.close();}
    }
    await fs.writeFile(path.join(out,'RESULT.txt'),`${passed} focused browser checks passed. Chromium desktop + emulated mobile WebKit; not a physical iPhone test. No live API, email, payment or application submission.\n`);
    console.log(`${passed} FOCUSED BROWSER CHECKS PASSED - NO PRODUCTION REQUESTS`);
  } finally {server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
