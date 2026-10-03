// Requires an isolated preview build with all locales enabled; never changes publication flags.
// Every external request is blocked. Quotes and instruction API responses are synthetic.
const {chromium}=require(process.env.ACT_PLAYWRIGHT_MODULE || 'playwright');
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const assert=require('node:assert/strict');
const preview=process.env.ACT_PREVIEW_DIR;
assert(preview && path.resolve(preview)!==path.resolve('.'),'Use an isolated ACT_PREVIEW_DIR');
const origin='http://127.0.0.1:3013';
const locales=['en','ar','fr','de','es','tr','zh-CN'];
const choose={en:'Choose language',ar:'اختر اللغة',fr:'Choisir une langue',de:'Sprache wählen',es:'Elegir idioma',tr:'Dil seçin','zh-CN':'选择语言'};
const read=l=>require(`../src/dictionaries/${l}/home.json`);
const server=spawn(process.execPath,[path.resolve('node_modules/next/dist/bin/next'),'start','-H','127.0.0.1','-p','3013'],{cwd:preview,stdio:'ignore'});
const draft={routePoints:[{id:1,type:'pickup',point:{description:'Synthetic Heathrow London',place_id:'test-pickup',coordinates:{lat:51.47,lng:-0.45}}},{id:2,type:'dropoff',point:{description:'Synthetic London destination',place_id:'test-dropoff',coordinates:{lat:51.5,lng:-0.12}}}],formDetails:{date:'2026-11-15',time:'13:30',smallSuitcase:1,largeSuitcase:0,adults:1,children:0,infants:0,numberOfPassengers:1},passengerDetails:{fullName:'Synthetic ليلى 客户',email:'preview@example.invalid',countryCode:'+44 United Kingdom',mobileNumber:'7700900000'},childInfantTravel:{infantSeatOption:'',childSeatOption:''},flightDetails:{flightType:'',flightNumber:'',airline:'',landingTime:'',departureTime:'',pickupSignName:''},additionalRequirements:{notesToDriver:'Synthetic note'}};
let browser;
async function main(){
 let ready=false;
 for(let i=0;i<60;i++){try{if((await fetch(origin+'/de')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,500));}
 assert(ready,'Isolated all-language preview ready');
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1440,height:1000},{width:390,height:900}]){
  const context=await browser.newContext({viewport,serviceWorkers:'block'});
  const page=await context.newPage();page.setDefaultTimeout(15000);
  await context.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(url.origin!==origin&&url.origin!=='http://127.0.0.1:3001')return route.abort();
   if(url.pathname.endsWith('/api/trips/calculate-trip-cost/'))return route.fulfill({json:{distance_miles:20,distance_meters:32187,route_polyline:'',car_type:[{id:900001,name_en:'Standard PHV',name_ar:'سيارة عادية',desc_en:'',icon_url:'/images/logo.svg',max_passengers_count:4,base_trip_cost:80,transfer_fare:80,min_adjustment:0,airport_vat:0,airport_access_fee:0,regular_vat:0,total_cost:80,expected_trip_duration_minutes:50}]}});
   if(url.pathname.startsWith('/api/instruction-files/'))return route.fulfill({json:{success:true,data:{instruction_files:[]}}});
   if(url.pathname.startsWith('/api/')||req.method()!=='GET'||url.origin!==origin)return route.abort();
   return route.continue();
  });
  async function openLanguage(locale){
   let selector=page.getByRole('button',{name:choose[locale],exact:true}).filter({visible:true});
   if(!await selector.count())await page.getByRole('button',{name:read(locale).navbar.menuToggle,exact:true}).click();
   await page.getByRole('button',{name:choose[locale],exact:true}).filter({visible:true}).first().click();
  }
  for(const locale of locales){
   await page.goto(origin+'/'+locale+'?audit=1#book-now',{waitUntil:'networkidle'});
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert.equal(await page.locator('html').getAttribute('dir'),locale==='ar'?'rtl':'ltr');
   assert((await page.locator('body').innerText()).includes(read(locale).home.Book_Taxi.title));
   // All three footer policies must open an actual same-language PDF.
   for(const [kind,dict] of [['privacy-policy',read(locale).policy_and_terms.policy],['terms-and-conditions',read(locale).policy_and_terms.terms],['faq',read(locale).faqs]]){
    await page.getByRole('button',{name:dict.Open_button.trim(),exact:true}).last().click();
    await page.locator(`iframe[src="/documents/${locale}/${kind}.pdf"]`).waitFor();
    assert(await page.locator(`a[download][href="/documents/${locale}/${kind}.pdf"]`).count());
    await page.getByRole('button',{name:dict.button,exact:true}).click();
   }
   // Seed a route and check every distinct destination from this source locale.
   await page.evaluate(({locale,draft})=>sessionStorage.setItem('act:language-transfer:v1',JSON.stringify({destination:locale,expires:Date.now()+300000,draft})),{locale,draft});
   await page.reload({waitUntil:'networkidle'});
   for(const target of locales.filter(l=>l!==locale)){
    await openLanguage(locale);
    await page.locator(`button[lang="${target}"]`).filter({visible:true}).first().click();
    await page.waitForURL(`**/${target}?audit=1#book-now`);
    await page.waitForFunction(()=>sessionStorage.getItem('act:language-transfer:v1')===null);
    await page.locator('input').filter({visible:true}).first().waitFor();
    assert(await page.locator('input').evaluateAll(xs=>xs.some(i=>i.value==='Synthetic Heathrow London')),`${locale}→${target}: route`);
    assert((await page.locator('#ride-date').innerText()).includes('2026'),`${target}: restored date`);
    assert.equal(await page.locator('#small_suitcase').inputValue(),'1');
    assert(!(await page.locator('#ride-time').innerText()).includes(require('../src/dictionaries/customer-runtime.json')[target].selectTime));
    assert.equal((await context.cookies()).find(c=>c.name==='act_locale').value,target);
    // Return to source through the same selector before the next pair.
    await openLanguage(target);await page.locator(`button[lang="${locale}"]`).filter({visible:true}).first().click();
    await page.waitForURL(`**/${locale}?audit=1#book-now`);
    await page.waitForFunction(()=>sessionStorage.getItem('act:language-transfer:v1')===null);
   }
   if(process.env.ACT_SCREENSHOTS){fs.mkdirSync(process.env.ACT_SCREENSHOTS,{recursive:true});await page.screenshot({path:path.join(process.env.ACT_SCREENSHOTS,`${locale}-${viewport.width}.png`)});}
   console.log(`PASS ${locale} ${viewport.width}: page, legal PDFs and six language destinations`);
  }
  await context.close();
 }
 console.log('PASS: seven-language desktop/mobile pages, 42 legal-document openings, all 42 distinct language pairs per viewport and preserved synthetic route; no real provider calls');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();server.kill();});
