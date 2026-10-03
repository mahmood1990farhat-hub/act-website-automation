// Local production build only. Every non-local request is blocked; quote data is synthetic.
const {chromium}=require(process.env.ACT_PLAYWRIGHT_MODULE || 'playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const origin='http://127.0.0.1:3012';
const server=spawn(process.execPath,['node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3012'],{stdio:'ignore'});
const draft={routePoints:[{id:1,type:'pickup',point:{description:'Synthetic Heathrow London',place_id:'test-pickup',coordinates:{lat:51.47,lng:-0.45}}},{id:2,type:'dropoff',point:{description:'Synthetic London destination',place_id:'test-dropoff',coordinates:{lat:51.5,lng:-0.12}}}],formDetails:{date:'2026-11-15',time:'13:30',smallSuitcase:1,largeSuitcase:0,adults:1,children:0,infants:0,numberOfPassengers:1},passengerDetails:{fullName:'Synthetic ليلى',email:'preview@example.invalid',countryCode:'+44 United Kingdom',mobileNumber:'7700900000'},childInfantTravel:{infantSeatOption:'',childSeatOption:''},flightDetails:{flightType:'',flightNumber:'',airline:'',landingTime:'',departureTime:'',pickupSignName:''},additionalRequirements:{notesToDriver:'Synthetic note'}};
let browser;
async function main(){
 let ready=false;
 for(let i=0;i<40;i++){try{if((await fetch(origin+'/en')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,500));}
 assert(ready,'Local server ready');
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1440,height:1000},{width:390,height:900}]){
  const context=await browser.newContext({viewport,serviceWorkers:'block'});
  const page=await context.newPage();page.setDefaultTimeout(15000);
  await context.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(url.origin!==origin&&url.origin!=='http://127.0.0.1:3001')return route.abort();
   if(url.pathname.endsWith('/api/trips/calculate-trip-cost/'))return route.fulfill({json:{distance_miles:20,distance_meters:32187,route_polyline:'',car_type:[{id:900001,name_en:'Synthetic vehicle',name_ar:'سيارة تجريبية',desc_en:'Synthetic only',icon_url:'/images/logo.svg',max_passengers_count:4,base_trip_cost:80,transfer_fare:80,min_adjustment:0,airport_vat:0,airport_access_fee:0,regular_vat:0,total_cost:80,expected_trip_duration_minutes:50}]}});
   if(url.pathname.startsWith('/api/')||req.method()!=='GET'||url.origin!==origin)return route.abort();
   return route.continue();
  });
  await page.goto(origin+'/en?audit=1#book-now',{waitUntil:'networkidle'});
  await page.evaluate(draft=>sessionStorage.setItem('act:language-transfer:v1',JSON.stringify({destination:'en',expires:Date.now()+300000,draft})),draft);
  await page.reload({waitUntil:'networkidle'});
  await page.getByRole('status').filter({hasText:'Your booking details were kept'}).waitFor();
  assert.equal(await page.locator('input').filter({visible:true}).count()>0,true);
  // Desktop and mobile selectors may both exist; use the visible selector.
  const openLanguage = async locale => {
    const name = locale === 'ar' ? 'اختر اللغة' : 'Choose language';
    const selector = page.getByRole('button', {name, exact:true}).filter({visible:true});
    if (!await selector.count()) {
      const menu = require(`../src/dictionaries/${locale}/home.json`).navbar.menuToggle;
      await page.getByRole('button', {name:menu,exact:true}).click();
    }
    await page.getByRole('button', {name, exact:true}).filter({visible:true}).first().click();
  };
  await openLanguage('en');
  await page.locator('button[lang="ar"]').filter({visible:true}).first().click();
  await page.waitForURL('**/ar?audit=1#book-now');
  await page.getByRole('status').filter({hasText:'تم الاحتفاظ'}).waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'),'ar');
  assert(await page.locator('input').evaluateAll(inputs=>inputs.some(i=>i.value==='Synthetic Heathrow London')));
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('act:language-transfer:v1')),null);
  await openLanguage('ar');
  await page.locator('button[lang="en"]').filter({visible:true}).first().click();
  await page.waitForURL('**/en?audit=1#book-now');
  await page.getByRole('status').filter({hasText:'Your booking details were kept'}).waitFor();
  const values=await page.locator('input').evaluateAll(inputs=>inputs.map(i=>i.value));
  assert(values.includes('Synthetic Heathrow London'));assert(values.includes('Synthetic London destination'));
  // Verify that unavailable tab storage blocks navigation rather than losing data.
  await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new Error('Test storage unavailable')};});
  await openLanguage('en');
  await page.locator('button[lang="ar"]').filter({visible:true}).first().click();
  await page.getByRole('alert').filter({hasText:'We could not keep your booking details'}).waitFor();
  assert(new URL(page.url()).pathname==='/en');
  await context.close();
 }
 console.log('PASS: desktop/mobile EN↔AR language switching preserves route state, URL query/fragment, consumes transfer and blocks navigation on storage failure; all provider calls blocked/mocked');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();server.kill();});
