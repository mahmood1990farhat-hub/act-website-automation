// Requires an isolated preview build with all locales enabled; never changes publication flags.
// Every external request is blocked. Quotes and instruction API responses are synthetic.
const {chromium}=require(process.env.ACT_PLAYWRIGHT_MODULE || 'playwright');
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const assert=require('node:assert/strict');
const preview=process.env.ACT_PREVIEW_DIR;
assert(preview && path.resolve(preview)!==path.resolve('.'),'Use an isolated ACT_PREVIEW_DIR');
const origin='http://127.0.0.1:3015';
require('../scripts/check-booking-language.cjs');
const {bookingText}=require('../src/components/_components/bookTaxi/booking-text.ts');
const locales=['en','ar','fr','de','es','tr','zh-CN'];
const choose={en:'Choose language',ar:'اختر اللغة',fr:'Choisir une langue',de:'Sprache wählen',es:'Elegir idioma',tr:'Dil seçin','zh-CN':'选择语言'};
const read=l=>require(`../src/dictionaries/${l}/home.json`);
const server=spawn(process.execPath,[path.resolve('node_modules/next/dist/bin/next'),'start','-H','127.0.0.1','-p','3015'],{cwd:preview,stdio:'ignore'});
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
  for(const locale of locales){
   const dict=read(locale), copy=require('../src/dictionaries/customer-runtime.json')[locale];
   await page.goto(origin+'/'+locale+'#book-now',{waitUntil:'networkidle'});
   const seeded={...draft,formDetails:{...draft.formDetails,adults:2,children:1,infants:1,numberOfPassengers:4,largeSuitcase:2},childInfantTravel:{infantSeatOption:'',childSeatOption:''}};
   await page.evaluate(({locale,draft})=>sessionStorage.setItem('act:language-transfer:v1',JSON.stringify({destination:locale,expires:Date.now()+300000,draft})),{locale,draft:seeded});
   await page.reload({waitUntil:'networkidle'});
   await page.waitForFunction(()=>sessionStorage.getItem('act:language-transfer:v1')===null);
   assert.equal(await page.locator('#adult-count').inputValue(),'2');
   assert.equal(await page.locator('#child-count').inputValue(),'1');
   assert.equal(await page.locator('#infant-count').inputValue(),'1');
   assert.equal(await page.locator('#large_suitcase').inputValue(),'2');
   assert((await page.locator('#ride-date').innerText()).includes('2026'));
   await page.getByRole('button',{name:dict.home.Book_Taxi.form.button.trim(),exact:true}).click();
   await page.getByText(copy.standardVehicle,{exact:true}).click();
   await page.locator('#passenger-full-name').waitFor();
   assert.equal(await page.locator('#passenger-full-name').inputValue(),draft.passengerDetails.fullName);
   assert.equal(await page.locator('#passenger-country-code').inputValue(),'+44 United Kingdom');
   await page.getByRole('button',{name:bookingText(locale,'Continue'),exact:true}).click();
   await page.locator('input[name="infant-seat-option"]').first().waitFor();
   await page.getByRole('button',{name:bookingText(locale,'Continue'),exact:true}).click();
   await page.getByText(bookingText(locale,'Please select the required child or infant seat option before continuing.'),{exact:true}).waitFor();
   await page.locator('input[name="infant-seat-option"][value="I will provide my own infant seats"]').check();
   await page.locator('input[name="child-seat-option"][value="I would like ACT to provide child seats"]').check();
   await page.getByRole('button',{name:bookingText(locale,'Continue'),exact:true}).click();
   await page.getByRole('button',{name:bookingText(locale,'Skip — Not applicable for this journey'),exact:true}).click();
   await page.locator('#notes-to-driver').waitFor();
   assert.equal(await page.locator('#notes-to-driver').inputValue(),'Synthetic note');
   await page.getByRole('button',{name:dict.home.Additional_Information.continue,exact:true}).click();
   await page.getByText(dict.home.Confir_flight_details.title,{exact:true}).waitFor();
   assert((await page.locator('body').innerText()).includes(draft.passengerDetails.fullName));
   // Legal text is also available at checkout; never press payment/create-booking controls.
   if(process.env.ACT_SCREENSHOTS){fs.mkdirSync(process.env.ACT_SCREENSHOTS,{recursive:true});await page.screenshot({path:path.join(process.env.ACT_SCREENSHOTS,`review-${locale}-${viewport.width}.png`)});}
   console.log(`PASS ${locale} ${viewport.width}: route, quote, passenger, child seats, flight skip, notes, review; stopped before booking/payment`);
  }
  await context.close();
 }
 console.log('PASS: fourteen seven-language desktop/mobile synthetic booking journeys to review, no booking/payment/email created');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();server.kill();});
