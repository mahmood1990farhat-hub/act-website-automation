const {chromium} = require('/opt/browser-test/node_modules/playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const origin = 'http://127.0.0.1:3001';
const out = '/tmp/french-previews';
fs.mkdirSync(out, {recursive:true});
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3001'],{stdio:'inherit'});
let browser;
async function main(){
 let ready=false;
 for(let i=0;i<45;i++){try{if((await fetch(origin+'/fr')).ok){ready=true;break;}}catch{} await new Promise(r=>setTimeout(r,1000));}
 assert.ok(ready,'preview ready');
 for(const slug of ['heathrow','gatwick','stansted','luton','london-city']){
  const response=await fetch(`${origin}/fr/${slug}-airport-transfer`);assert.equal(response.status,200);
  const html=await response.text(); assert.match(html,/<html[^>]*lang="fr"[^>]*dir="ltr"/);
  assert.match(html,/<meta[^>]*name="robots"[^>]*content="noindex, nofollow"/);
  const schemas=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m=>JSON.parse(m[1]));
  const graph=schemas.find(s=>s['@graph'])?.['@graph'];
  assert.ok(graph,'French airport structured data');
  assert.equal(graph.find(s=>s['@type']==='WebPage').inLanguage,'fr');
  assert.equal(graph.find(s=>s['@type']==='FAQPage').mainEntity.length,4);
  assert.ok(html.includes('Transfert aéroport'));assert.ok(html.includes('href="/fr#book-now"'));
 }
 for(const [route,title] of [['download-app','Application ACT'],['complaints','Réclamations'],['lost-property','Objets perdus']]){
  const html=await (await fetch(origin+'/fr/'+route)).text();
  assert.ok(html.includes(title),route+' French metadata');
  assert.match(html,/<meta[^>]*name="robots"[^>]*content="noindex, nofollow"/);
 }
 const sitemap=await (await fetch(origin+'/sitemap.xml')).text();assert.ok(!sitemap.includes('/fr'));
 for(const lang of ['de','tr','es','zh-CN'])assert.equal((await fetch(origin+'/'+lang)).status,404);
 const op=await fetch(origin+'/fr/auth?captain=1',{redirect:'manual'});assert.ok(op.headers.get('location').includes('/en/auth?captain=1'));
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const errors=[],requests=[];
 for(const [device,viewport] of [['desktop',{width:1440,height:1050}],['mobile',{width:390,height:1000}]]){
  const context=await browser.newContext({viewport,serviceWorkers:'block'});
  await context.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(req.method()!=='GET')requests.push({method:req.method(),path:url.pathname});
   if(url.origin!==origin)return route.abort();
   if(url.pathname==='/api/places')return route.fulfill({json:{status:'OK',predictions:[{description:'Synthetic Heathrow Airport, London, UK',place_id:'synthetic-only',reference:'synthetic-only',matched_substrings:[]}]}});
   if(url.pathname==='/api/place-details')return route.fulfill({json:{result:{geometry:{location:{lat:51.5074,lng:-0.1278}}}}});
   if(url.pathname.endsWith('/api/trips/calculate-trip-cost/'))return route.fulfill({json:{distance_miles:20,distance_meters:32187,route_polyline:'',car_type:[{id:900001,name_en:'Preview vehicle — synthetic data',name_ar:'سيارة تجريبية',desc_en:'Synthetic vehicle for private preview only.',icon_url:'/images/logo.svg',max_passengers_count:4,base_trip_cost:80,transfer_fare:80,min_adjustment:0,airport_vat:0,airport_access_fee:0,regular_vat:0,total_cost:80,expected_trip_duration_minutes:50}]}});
   if(url.pathname.startsWith('/api/')||req.method()!=='GET')return route.abort();
   return route.continue();
  });
  const page=await context.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
  for(const locale of ['en','fr'])for(const [name,path] of [['home',''],['heathrow','/heathrow-airport-transfer']]){
   await page.goto(origin+'/'+locale+path,{waitUntil:'networkidle'});
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   if(locale==='fr')assert.ok(await page.getByTestId('french-preview-notice').isVisible());
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'No horizontal page overflow '+device+locale+path);
   await page.screenshot({path:`${out}/${locale}-${name}-${device}.png`});
   if(locale==='fr'&&name==='heathrow')await page.screenshot({path:`${out}/fr-heathrow-${device}-full.png`,fullPage:true});
  }
  await page.goto(origin+'/fr/heathrow-airport-transfer',{waitUntil:'networkidle'});
  await page.locator('article a[href="/fr/about-us#contact-us"]').click();await page.locator('#contact-us').waitFor({state:'visible'});
  assert.equal(await page.getByTestId('french-contact').locator('a[href="mailto:info@airportandcitytransfer.com"]').count(),1);
  assert.equal(await page.getByTestId('french-contact').locator('form').count(),0);
  await page.screenshot({path:`${out}/fr-contact-${device}.png`});
  await page.goto(origin+'/fr/auth',{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Se connecter',exact:true}).click();
  assert.ok(await page.getByText('Champ obligatoire',{exact:true}).count()>=2);
  assert.equal(await page.locator('form').evaluate(el=>getComputedStyle(el).direction),'ltr');
  await page.getByText('Créer un compte',{exact:true}).click();
  await page.getByRole('heading',{name:'Créer un compte',exact:true}).waitFor();
  assert.equal(await page.locator('select option[value="FR"]').innerText(),'France');
  await page.locator('select').selectOption('FR');
  assert.ok((await page.locator('input[type="tel"]').inputValue()).includes('+33'));
  await page.screenshot({path:`${out}/fr-signup-${device}.png`});
  await page.goto(origin+'/fr/auth',{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Chauffeur',exact:true}).click();
  await page.waitForURL('**/en/auth?captain=1');
  for(const [route,tab,submit] of [['complaints','Envoyer une réclamation','Envoyer la réclamation'],['lost-property','Faire une déclaration','Envoyer la déclaration']]){
   await page.goto(origin+'/fr/'+route,{waitUntil:'domcontentloaded'});
   await page.getByRole('button',{name:tab,exact:true}).waitFor({state:'visible'});
   await page.getByRole('button',{name:tab,exact:true}).click();
   // Empty submission exercises client validation only; no support request is sent.
   await page.getByRole('button',{name:submit,exact:true}).click();
   await page.getByText('Veuillez sélectionner un trajet',{exact:true}).waitFor();
  }
  await page.goto(origin+'/fr#book-now',{waitUntil:'networkidle'});
  for(const placeholder of ['Rechercher un lieu à Londres…','Rechercher un lieu au Royaume-Uni…']){
   const field=page.getByPlaceholder(placeholder,{exact:true});await field.fill('Synthetic London');
   const response=page.waitForResponse(r=>r.url().includes('/api/place-details'));
   await page.getByText('Synthetic Heathrow Airport, London, UK',{exact:true}).first().click();await response;
  }
  await page.getByRole('button',{name:'Choisir une date',exact:true}).click();
  // Move to next month using the actual calendar control; stored format stays unchanged.
  await page.locator('button').filter({has:page.locator('svg.lucide-chevron-right')}).last().click();
  await page.getByRole('button',{name:'15',exact:true}).click();await page.getByRole('button',{name:'Valider',exact:true}).click();
  assert.equal(await page.locator('#ride-time').innerText(),'Choisir une heure');
  await page.locator('#ride-time').click();await page.getByRole('button',{name:'Valider',exact:true}).click();
  await page.getByRole('button',{name:'Obtenir un tarif',exact:true}).click();
  await page.getByText('Preview vehicle — synthetic data',{exact:true}).click();
  await page.getByText('Coordonnées du passager',{exact:true}).waitFor();
  const country=page.locator('#passenger-country-code');
  assert.equal(await country.inputValue(),'+44 United Kingdom');
  for(const value of ['+33 France','+32 Belgium','+41 Switzerland','+1 Canada','+49 Germany','+34 Spain','+86 China']){
   assert.equal(await country.locator(`option[value="${value}"]`).count(),1,value+' phone choice');
  }
  assert.equal(await country.locator('option[value^="+90 "]').count(),1);
  await country.selectOption('+33 France');
  await page.screenshot({path:`${out}/fr-passenger-${device}.png`});
  await page.getByRole('button',{name:'Continuer',exact:true}).click();
  await page.getByText('Le nom du passager, l’adresse e-mail, l’indicatif du pays et le numéro de téléphone portable sont obligatoires.',{exact:true}).waitFor();
  await page.locator('#passenger-full-name').fill('Passager Démonstration');await page.locator('#passenger-email').fill('preview@example.invalid');await page.locator('#passenger-mobile').fill('612345678');
  await page.getByRole('button',{name:'Continuer',exact:true}).click();
  await page.getByText('Informations sur le vol',{exact:true}).waitFor();
  await page.screenshot({path:`${out}/fr-flight-${device}.png`});
  await page.getByRole('button',{name:'Passer — Sans objet pour ce trajet',exact:true}).click();
  await page.locator('#notes-to-driver').waitFor();await page.getByRole('button',{name:'Continuer',exact:true}).click();
  await page.getByText('Vérifiez les détails de votre trajet avant de continuer',{exact:true}).waitFor();
  assert.ok(await page.getByRole('button',{name:'Confirmer et continuer',exact:true}).isVisible());
  assert.ok((await page.locator('body').innerText()).includes('+33 France 612345678'));
  // Deliberately stop before the booking/payment creation button.
  console.log('PASS',device,'French navigation, dates, simulated quote, passenger validation, flight, notes and review; stopped before booking');
  await context.close();
 }
 assert.equal(requests.length,2,'Only the two simulated quotes may be attempted');
 assert.ok(requests.every(r=>r.path.endsWith('/api/trips/calculate-trip-cost/')));
 assert.deepEqual(errors.filter(e=>e!=='Failed to load Stripe.js'),[]);
 const result={status:'PASS',airportPages:5,viewports:2,simulatedQuotes:requests.length,realBookings:0,payments:0,knownOfflineStripeErrors:errors.filter(e=>e==='Failed to load Stripe.js').length,limitations:['Network isolated; real Maps/Stripe/backend not accepted','Policy source claims still require review','Screenshots compare English and French in the same candidate build, not a new production capture']};
 fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
