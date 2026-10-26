/* Actual review/card components; only unrelated UI and Stripe Elements are mocked.
 * Synthetic API on loopback. No production services, secrets, payments or emails.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {build} = require('esbuild');
const {chromium, webkit, devices} = require('playwright');
const postcss = require('postcss');
const tailwind = require('@tailwindcss/postcss');
const root = path.resolve(__dirname,'../..'), out=path.join(root,'.checkout-terms-test');
const TEXT='SYNTHETIC TEST TERMS ONLY — NOT A PUBLISHED POLICY.\nFull refund >24 hours; 50% >12–24 hours; 0% <=12 hours, subject to the reviewed fair-loss safeguard.\n<script>window.untrustedTermsExecuted=true</script>';
const doc=(locale='en',version='synthetic-v1')=>{
  const text=locale==='ar'?'نص شروط اصطناعي للاختبار فقط — ليس للنشر.\n'+TEXT:TEXT;
  const body=version==='synthetic-v2'?text+'\nSynthetic revision two.':text;
  return {schema:1,enabled:true,terms_version:version,terms_sha256:crypto.createHash('sha256').update(body).digest('hex'),locale,text:body,document_url:`/documents/${locale}/${version}.pdf`,pdf_sha256:'a'.repeat(64),effective_at:'2026-01-01T00:00:00+00:00'};
};
const PAYMENT={client_secret:'pi_synthetic1_secret_synthetic',price_breakdown:{total_cost:100.01}};
const wait=async(page,fn)=>page.waitForFunction(fn);
const agree=page=>page.locator('#act-review-terms').locator('..').locator('input[type=checkbox]');
const proceed=page=>page.getByRole('button',{name:/^(Confirm & Continue|التأكيد و المتابعة)$/});
async function ready(page){await page.locator('#act-review-terms').waitFor();}
async function start(page){await ready(page);await agree(page).check();await proceed(page).click();await page.locator('#act-payment-terms').waitFor();}
async function completeCards(page){for(const label of ['Synthetic card','Synthetic expiry','Synthetic cvc'])await page.getByLabel(label).fill('ok');}
async function forceSubmit(page){await page.locator('form').evaluate(f=>f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));}

const cases=[
 ['unchecked agreement blocks initiation; exact text escaped and PDF version shown',async({page,state,origin,name})=>{
   await page.goto(origin);await ready(page);assert.equal(await agree(page).isChecked(),false);
   assert.equal(await proceed(page).isDisabled(),true);assert.equal(state.posts.length,0);
   assert.equal(await page.locator('#act-review-terms [role=region]').textContent(),TEXT);
   assert.equal(await page.evaluate(()=>window.untrustedTermsExecuted),undefined);
   assert.equal(await page.getByRole('link',{name:'Download these terms (PDF)'}).getAttribute('href'),'/documents/en/synthetic-v1.pdf');
   assert.equal(await page.getByText(/at least 3 hours before/).count(),0);
   await agree(page).check();await agree(page).uncheck();assert.equal(await proceed(page).isDisabled(),true);
   await page.locator('#act-review-terms').locator('..').screenshot({path:path.join(out,`${name}-consent.png`)});
 }],
 ['guest acknowledgement reaches initiation; final payment keeps same terms and checks agreement',async({page,state,origin,name})=>{
   await page.goto(origin);await start(page);assert.equal(state.posts.length,1);
   const p=state.posts[0];assert.equal(p.path,'/api/trips/initiate-guest-payment/');
   assert.deepEqual(p.body.booking_terms_acknowledgement,{accepted:true,terms_version:'synthetic-v1',terms_sha256:doc().terms_sha256,locale:'en'});
   assert.deepEqual(p.body.stop_points,[{point_lat:2,point_lng:3}]);assert.equal(p.authorization,undefined);
   state.version='synthetic-v2';const gets=state.gets.length;
   assert.equal(await page.locator('#act-payment-terms [role=region]').textContent(),TEXT);
   assert.equal(await page.getByRole('button',{name:'Existing privacy notice'}).count(),1);
   assert.equal(await page.getByRole('button',{name:'Legacy terms'}).count(),0);
   await completeCards(page);await forceSubmit(page);assert.equal(await page.evaluate(()=>window.confirmCalls.length),0);
   await page.getByRole('checkbox',{name:'I agree'}).check();
   await page.locator('form').evaluate(f=>{f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));});
   await wait(page,()=>window.confirmCalls.length===1);assert.equal(state.gets.length,gets);
   assert.equal(await page.evaluate(()=>window.confirmCalls[0]),PAYMENT.client_secret);
   assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length})),{local:0,session:0});
   await page.locator('#act-payment-terms').screenshot({path:path.join(out,`${name}-payment.png`)});
 }],
 ['registered checkout uses the existing authenticated route and same four-field acknowledgement',async({page,state,origin,context})=>{
   await context.addCookies([{name:'userToken',value:'synthetic-token',url:origin}]);
   await page.goto(origin);await start(page);assert.equal(state.posts.length,1);
   assert.equal(state.posts[0].path,'/api/trips/initiate-payment/');
   assert.equal(state.posts[0].authorization,'Bearer synthetic-token');
   assert.deepEqual(Object.keys(state.posts[0].body.booking_terms_acknowledgement).sort(),['accepted','locale','terms_sha256','terms_version']);
 }],
 ['changed public terms clear agreement before any payment request',async({page,state,origin})=>{
   await page.goto(origin);await ready(page);await agree(page).check();state.version='synthetic-v2';await proceed(page).click();
   await page.getByText('Synthetic revision two.',{exact:false}).waitFor();
   assert.equal(await agree(page).isChecked(),false);assert.equal(state.posts.length,0);
   await agree(page).check();await proceed(page).click();await page.locator('#act-payment-terms').waitFor();
   assert.equal(state.posts[0].body.booking_terms_acknowledgement.terms_version,'synthetic-v2');
 }],
 ['material booking changes reset consent without changing existing payload fields',async({page,state,origin})=>{
   await page.goto(origin);await ready(page);await agree(page).check();
   await page.evaluate(()=>window.fixture.change({time:'14:30'}));
   await page.waitForFunction(()=>!document.querySelector('#act-review-terms')?.parentElement.querySelector('input')?.checked);
   await ready(page);assert.equal(await agree(page).isChecked(),false);assert.equal(state.posts.length,0);
   await agree(page).check();await proceed(page).click();await page.locator('#act-payment-terms').waitFor();
   assert.equal(state.posts[0].body.trip_time,'14:30');
 }],
 ['malformed, wrong-language, unsafe-path and wrong-hash descriptors never become legacy mode',async({page,state,origin})=>{
   for(const override of [{schema:2},{enabled:'false'},{locale:'fr'},{terms_sha256:'b'.repeat(64)},{document_url:'https://example.invalid/x.pdf'},{pdf_sha256:'bad'}]){
     state.override=override;await page.goto(origin);await page.getByRole('alert').waitFor();
     assert.equal(await proceed(page).isDisabled(),true);assert.equal(state.posts.length,0);
   }
 }],
 ['unavailable discovery stops checkout; explicit retry performs only a GET',async({page,state,origin})=>{
   state.getStatus=503;await page.goto(origin);await page.getByRole('alert').waitFor();
   assert.equal(await proceed(page).isDisabled(),true);state.getStatus=200;
   await page.getByRole('button',{name:'Reload terms'}).click();await ready(page);
   assert.equal(state.posts.length,0);assert.equal(await agree(page).isChecked(),false);
 }],
 ['explicit disabled response alone preserves the existing legacy consent path',async({page,state,origin})=>{
   state.disabled=true;await page.goto(origin);await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Confirm & Continue')&&!b.disabled));
   await proceed(page).click();await page.getByRole('button',{name:'Legacy terms'}).waitFor();
   assert.equal(state.posts.length,1);assert.equal('booking_terms_acknowledgement' in state.posts[0].body,false);
   assert.equal(await page.getByRole('checkbox',{name:'I agree'}).isChecked(),false);
   await completeCards(page);await forceSubmit(page);assert.equal(await page.evaluate(()=>window.confirmCalls.length),0);
 }],
 ['rapid repeat clicks initiate once and keep navigation locked while pending',async({page,state,origin})=>{
   state.postDelay=600;await page.goto(origin);await ready(page);await agree(page).check();
   await proceed(page).evaluate(b=>{b.click();b.click();b.click();});
   assert.equal(await page.getByRole('button',{name:'Back',exact:true}).isDisabled(),true);
   await page.locator('#act-payment-terms').waitFor();assert.equal(state.posts.length,1);
 }],
 ['uncertain initiation is held without automatic or repeat-click retries',async({page,state,origin})=>{
   state.postStatus=503;await page.goto(origin);await ready(page);await agree(page).check();await proceed(page).click();
   await page.getByText(/Do not submit again/).waitFor();assert.equal(state.posts.length,1);
   await proceed(page).evaluate(b=>b.click());assert.equal(state.posts.length,1);
   assert.equal(await proceed(page).isDisabled(),true);assert.equal(await page.getByRole('button',{name:'Back',exact:true}).isDisabled(),true);
 }],
 ['returning to unchanged review reuses the same prepared payment and accepted version',async({page,state,origin})=>{
   await page.goto(origin);await start(page);state.version='synthetic-v2';const gets=state.gets.length;
   await page.evaluate(()=>window.fixture.review());await ready(page);assert.equal(await agree(page).isChecked(),false);
   await agree(page).check();await proceed(page).click();await page.locator('#act-payment-terms').waitFor();
   assert.equal(state.posts.length,1);assert.equal(state.gets.length,gets);
   assert.equal(await page.locator('#act-payment-terms [role=region]').textContent(),TEXT);
 }],
 ['language change rejects delayed old results and requires fresh localised agreement',async({page,state,origin})=>{
   state.getDelay=300;await page.goto(origin);await page.waitForFunction(()=>!!window.fixture);
   await page.evaluate(()=>window.fixture.language('ar'));await page.locator('#act-review-terms[lang=ar]').waitFor();
   assert.equal(await agree(page).isChecked(),false);assert.equal(await page.locator('#act-review-terms').getAttribute('dir'),'rtl');
   await agree(page).check();await proceed(page).click();await page.locator('#act-payment-terms').waitFor();
   assert.equal(state.posts[0].body.booking_terms_acknowledgement.locale,'ar');
   assert.equal(await page.locator('#act-payment-terms [role=region]').textContent(),doc('ar').text);
 }],
 ['card screen without a matching prepared terms session cannot charge even by implicit submit',async({page,state,origin})=>{
   await page.goto(origin+'/?final=1');await page.getByText(/terms for this payment are unavailable/).waitFor();
   await completeCards(page);await forceSubmit(page);assert.equal(await page.evaluate(()=>window.confirmCalls.length),0);
   assert.equal(state.posts.length,0);assert.equal(state.gets.length,0);
 }],
 ['booking change during pre-initiation terms recheck prevents stale payment creation',async({page,state,origin})=>{
   await page.goto(origin);await ready(page);await agree(page).check();state.getDelay=300;await proceed(page).click();
   await page.evaluate(()=>window.fixture.change({time:'16:00'}));await page.waitForTimeout(500);
   assert.equal(state.posts.length,0);await ready(page);assert.equal(await agree(page).isChecked(),false);
 }],
];

async function main(){
 await fs.mkdir(out,{recursive:true});
 const entry=`import React,{useEffect,useState} from 'react';import{createRoot}from'react-dom/client';
 import Review from '../src/components/_components/bookTaxi/ConfirmFlightDetails';
 import Checkout from '../src/components/_components/stripe/CheckoutForm';
 import{CheckoutTermsProvider}from'../src/components/_components/bookTaxi/CheckoutTerms';
 window.confirmCalls=[];
 const initial={routePoints:[{type:'pickup',point:{description:'Synthetic pickup',coordinates:{lat:0,lng:1}}},{type:'stop',point:{description:'Synthetic stop',coordinates:{lat:2,lng:3}}},{type:'dropoff',point:{description:'Synthetic destination',coordinates:{lat:4,lng:5}}}],time:'12:00',date:'2026-11-12',carName:'Synthetic vehicle',carImage:'',distance:'10 mi',smallSuitcase:1,largeSuitcase:1,adults:1,children:0,infants:0,numberOfPassengers:1,passengerDetails:{fullName:'Synthetic Passenger',email:'synthetic@example.invalid',countryCode:'+44',mobileNumber:'07700900123'},childInfantTravel:{infantSeatOption:'',childSeatOption:''},flightDetails:{flightType:'',flightNumber:'',airline:'',landingTime:'',departureTime:'',pickupSignName:''},additionalRequirements:{notesToDriver:''},cartype:1,cost:100.01,total_cost:100.01};
 const trans={Confir_flight_details:{cost_breakdown:'Price',transfer_fare:'Fare',airport_access_fee:'Airport',vat_20:'VAT',total_price:'Total'},Additional_Information:{title:'Additional information',driverTitle:'Notes'}};
 function Harness(){const[data,setData]=useState(initial),[locale,setLocale]=useState('en'),[step,setStep]=useState(new URLSearchParams(location.search).has('final')?8:7),[secret,setSecret]=useState('pi_missing_secret_missing'),[total,setTotal]=useState(100.01);
 useEffect(()=>{window.fixture={change:x=>setData(d=>({...d,...x})),language:setLocale,review:()=>setStep(7)}},[]);
 return <main style={{padding:20,maxWidth:1100,margin:'auto'}}><p>Synthetic isolated checkout test — not the live website</p>{step===8?<Checkout nextStep={()=>{}} prevStep={()=>setStep(7)} clientSecret={secret} bookingTotal={total} currency='GBP' locale={locale} policy_and_terms={{policy:{},terms:{}}} trans={{title:'Synthetic card payment',subtitle:'No real card details',form:{Card_Number:'Card',Expired_date:'Expiry',check:{Agree:'I agree'},button:'Pay test'}}}/>:<Review trans={trans} data={data} locale={locale} rideOptions={null} step={7} setStep={setStep} editDatelis={()=>setData(d=>({...d,time:'15:00'}))} setClientSecret={setSecret} setPaymentTotal={setTotal}/>}</main>}
 createRoot(document.getElementById('root')).render(<CheckoutTermsProvider><Harness/></CheckoutTermsProvider>);`;
 await fs.writeFile(path.join(out,'entry.tsx'),entry);
 const stub={name:'isolated-boundaries',setup(b){
   b.onResolve({filter:/^(next\/image|@stripe\/react-stripe-js|@\/lib\/customer-text|@\/lib\/customer-runtime)$/},a=>({path:a.path,namespace:'stub'}));
   b.onResolve({filter:/(^|\/)(MapView|CarLoading|MoneyCountingHand|Policy|Terms)$/},a=>({path:a.path,namespace:'stub'}));
   b.onLoad({filter:/.*/,namespace:'stub'},a=>{
     let contents;
     if(a.path==='@stripe/react-stripe-js')contents=`import React from 'react';const input=(name)=>({onChange})=><input aria-label={name} onChange={e=>onChange({complete:e.target.value==='ok'})}/>;export const CardNumberElement=input('Synthetic card'),CardExpiryElement=input('Synthetic expiry'),CardCvcElement=input('Synthetic cvc');export const useElements=()=>({getElement:()=>({})});export const useStripe=()=>({confirmCardPayment:async secret=>{window.confirmCalls.push(secret);await new Promise(r=>setTimeout(r,100));return{error:{code:'card_declined'}}}});`;
     else if(a.path==='@/lib/customer-text')contents='export const customerText=(locale,text)=>text;';
     else if(a.path==='@/lib/customer-runtime')contents='export const runtimeText=(locale,text)=>text;export const customerPaymentError=()=>"Synthetic decline";';
     else if(a.path.endsWith('/Policy'))contents=`import React from 'react';export default()=> <button type='button'>Existing privacy notice</button>;`;
     else if(a.path.endsWith('/Terms'))contents=`import React from 'react';export default()=> <button type='button'>Legacy terms</button>;`;
     else contents=`import React from 'react';export default()=> <span/>;`;
     return {contents,loader:'tsx',resolveDir:root};
   });
 }};
 await build({entryPoints:[path.join(out,'entry.tsx')],bundle:true,outfile:path.join(out,'app.js'),platform:'browser',jsx:'automatic',tsconfig:path.join(root,'tsconfig.json'),define:{'process.env':'{}','process.env.NODE_ENV':'"test"','process.env.NEXT_PUBLIC_API_BASE_URL':'""'},plugins:[stub]});
 const css=await postcss([tailwind({base:root})]).process('@import "tailwindcss";',{from:path.join(root,'src/app/globals.css')});
 await fs.writeFile(path.join(out,'app.css'),css.css);
 const server=http.createServer(async(req,res)=>{
   const p=(req.url||'').split('?')[0];
   if(p==='/app.js'||p==='/app.css'){res.setHeader('Content-Type',p.endsWith('.js')?'application/javascript':'text/css');res.end(await fs.readFile(path.join(out,p.slice(1))));return;}
   res.setHeader('Content-Type','text/html');res.end('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/app.css"><style>body{background:#101827;color:white;font-family:Arial}input{color:inherit}button{min-height:44px}svg{max-width:24px}</style></head><body><div id="root"></div><script src="/app.js"></script></body></html>');
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
 const results=[];
 try{
   for(const[name,engine,options]of[['desktop',chromium,{viewport:{width:1280,height:900}}],['mobile-webkit',webkit,{...devices['iPhone 13']}]] ){
     const browser=await engine.launch();
     try{for(const[label,test]of cases){const context=await browser.newContext(options);const page=await context.newPage();page.setDefaultTimeout(7000);page.setDefaultNavigationTimeout(10000);
       page.on('pageerror',error=>console.error('BROWSER ERROR:',error.message));
       const state={posts:[],gets:[],version:'synthetic-v1',override:{},getStatus:200,postStatus:200,getDelay:0,postDelay:0,disabled:false};
       await page.route('**/*',async route=>{
         const url=new URL(route.request().url());if(url.origin!==origin){await route.abort();return;}
         if(url.pathname==='/api/payments/checkout-terms/'){
           state.gets.push(url.search);const body=state.disabled?{schema:1,enabled:false}:{...doc(url.searchParams.get('locale'),state.version),...state.override};
           await new Promise(r=>setTimeout(r,state.getDelay));await route.fulfill({status:state.getStatus,contentType:'application/json',body:JSON.stringify(body)});return;
         }
         if(url.pathname.includes('/initiate-')){
           state.posts.push({path:url.pathname,body:route.request().postDataJSON(),authorization:route.request().headers().authorization});
           await new Promise(r=>setTimeout(r,state.postDelay));await route.fulfill({status:state.postStatus,contentType:'application/json',body:JSON.stringify(state.postStatus===200?PAYMENT:{detail:'Synthetic outage'})});return;
         }
         await route.continue();
       });
       try{await test({page,state,origin,name,context});results.push(`${name}: PASS ${label}`);console.log(results.at(-1));}
       catch(e){await page.screenshot({path:path.join(out,`${name}-failure.png`),fullPage:true}).catch(()=>{});throw e;}
       finally{await context.close();}
     }}finally{await browser.close();}
   }
   const result=`${results.length} focused checkout-consent browser cases PASSED\n${process.env.GITHUB_SHA||'local'}\n${results.join('\n')}\n`;
   await fs.writeFile(path.join(out,'RESULT.txt'),result);console.log(result);
 }finally{await new Promise(r=>server.close(r));}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
