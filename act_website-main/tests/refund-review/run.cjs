/* Actual review component; local mocked API only, no real account or refund. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const esbuild = require('esbuild');
const { chromium, webkit } = require('playwright');
const out = path.resolve('.refund-review-test');
fs.mkdirSync(out, {recursive:true});
fs.writeFileSync(path.join(out,'entry.tsx'), `import React from 'react';import {createRoot} from 'react-dom/client';import Review from '../src/components/_components/dashboard/CancellationReviewDashboard';createRoot(document.getElementById('root')!).render(<Review token="synthetic-token"/>);`);
esbuild.buildSync({entryPoints:[path.join(out,'entry.tsx')],bundle:true,outfile:path.join(out,'bundle.js'),platform:'browser',jsx:'automatic',define:{'process.env.NEXT_PUBLIC_API_BASE_URL':'""','process.env.NODE_ENV':'"production"'}});
const server = http.createServer((req,res)=>{
  if(req.url==='/bundle.js'){res.setHeader('Content-Type','application/javascript');res.end(fs.readFileSync(path.join(out,'bundle.js')));}
  else {res.setHeader('Content-Type','text/html');res.end('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic ACT refund review</title></head><body style="margin:0;background:#0c1422"><div id="root"></div><script src="/bundle.js"></script></body></html>');}
});
const ids=['11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222'];
const clone=x=>JSON.parse(JSON.stringify(x));
function detail(i=0){return {operator_schema:1,cancellation_id:ids[i],trip_id:41+i,booking_reference:`ACT-0000${41+i}`,
  status:'cancelled',cancellation_received_at:'2026-11-03T12:00:00Z',stopped_at:'2026-11-03T12:00:01Z',
  refund_status:'manual_review',accounting_status:'manual_review',captured_pence:10001,currency:'GBP',hold_reason:'',terms_evidence:'recorded',
  terms:{terms_version:'synthetic-accepted-v1',policy_version:'act-cancellation-24h12h-v1',locale:'en',terms_sha256:'a'.repeat(64),accepted_at:'2026-11-01T12:00:00Z',pickup_at:'2026-11-04T08:00:00Z',terms_text:'Synthetic accepted terms. <script>window.BAD=1</script>'},
  operation:null,actions:{review:true,reconcile:false,reason:'Record evidenced net loss, then explicitly confirm. The backend determines any refund.'},read_at:'2026-11-03T12:00:02Z'};}
const row=d=>({cancellation_id:d.cancellation_id,trip_id:d.trip_id,booking_reference:d.booking_reference,journey_status:d.status,cancellation_received_at:d.cancellation_received_at,refund_status:d.refund_status,has_hold:!!d.hold_reason});
function state(d,status='pending') {d.refund_status=status;d.accounting_status=status==='succeeded'?'processed':status;d.actions={review:false,reconcile:true,reason:'An operation already exists. Do not send another refund.'};d.operation={status,amount_pence:5001,first_attempt_at:'2026-11-03T12:00:03Z',updated_at:'2026-11-03T12:00:04Z',accounting_posted:status==='succeeded'};}
async function waitText(page,text){await page.getByText(text,{exact:true}).first().waitFor();}
const results=[], browsers=[];
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const origin=`http://127.0.0.1:${server.address().port}`;
 for(const [name,engine,viewport] of [['desktop',chromium,{width:1440,height:1100}],['mobile-webkit',webkit,{width:390,height:844}]]){
  const browser=await engine.launch({headless:true}); browsers.push(browser);
  async function test(title,fn,setup=()=>{}){
   const context=await browser.newContext({viewport}); const page=await context.newPage(); page.setDefaultTimeout(10000);
   const s={details:[detail(),detail(1)],posts:[],gets:[],denied:false,empty:false,uncertain:false,slowFirst:false}; setup(s);
   await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.origin!==origin)return route.abort();
    if(!url.pathname.startsWith('/api/payments/cancellations/'))return route.continue();
    assert.equal(req.headers().authorization,'Bearer synthetic-token');
    const body=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
    if(s.denied)return route.fulfill({status:403,contentType:'application/json',body:'{"detail":"denied"}'});
    const id=url.pathname.split('/')[4];
    if(req.method()==='GET'){
      s.gets.push(url.pathname+url.search);
      if(!id){const ds=s.empty?[]:s.details.filter(d=>!url.searchParams.has('trip_id')||String(d.trip_id)===url.searchParams.get('trip_id'));return body({success:true,data:ds.map(row),pagination:{page:1,page_size:20,count:ds.length,has_next:false}});}
      if(s.slowFirst&&id===ids[0])await new Promise(r=>setTimeout(r,300));
      return body({success:true,data:clone(s.details.find(d=>d.cancellation_id===id))});
    }
    const payload=req.postDataJSON();s.posts.push({path:url.pathname,payload});
    const d=s.details.find(d=>d.cancellation_id===id);
    if(url.pathname.endsWith('/review/')){
      assert.deepEqual(Object.keys(payload).sort(),['review_reference','reviewed_net_loss_pence']);
      state(d,'pending');if(s.uncertain)return route.abort('failed');
    }else{assert.ok(url.pathname.endsWith('/reconcile/'));assert.deepEqual(payload,{});state(d,'succeeded');}
    return body({success:true,data:{refund_status:d.refund_status}});
   });
   try{await page.goto(origin);await fn(page,s);results.push(`${name}: PASS ${title}`);console.log(results.at(-1));}
   catch(err){await page.screenshot({path:path.join(out,`${name}-failure.png`),fullPage:true}).catch(()=>{});throw err;}
   finally{await context.close();}
  }
  const select=async p=>{await p.getByRole('button',{name:/ACT-000041/}).click();await p.getByRole('heading',{name:'ACT-000041'}).waitFor();};
  const fill=async p=>{await p.getByLabel('Reviewed net loss (GBP)').fill('50.00');await p.getByLabel('Evidence / case reference').fill('synthetic-evidence-001');await p.getByRole('button',{name:'Review entered details'}).click();};
  await test('read-only search, saved terms and responsive evidence',async(p,s)=>{
    await select(p);assert.equal(s.posts.length,0);
    await waitText(p,'£100.01');await waitText(p,'synthetic-accepted-v1');
    await p.getByText('View the recorded terms',{exact:true}).click();
    assert.equal(await p.evaluate(()=>window.BAD),undefined);
    await p.getByLabel('Trip ID (optional)').fill('41');await p.getByRole('button',{name:'Find cases'}).click();
    await p.getByRole('button',{name:/ACT-000042/}).waitFor({state:'detached'});
    await p.getByRole('button',{name:/ACT-000041/}).waitFor();assert.equal(await p.getByRole('button',{name:/ACT-000042/}).count(),0);
    await select(p);await p.screenshot({path:path.join(out,`${name}-review.png`),fullPage:true});
    assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
    assert.equal(s.posts.length,0);
  });
  await test('validation and deliberate confirmation; rapid clicks send one POST',async(p,s)=>{
    await select(p);await p.getByLabel('Reviewed net loss (GBP)').fill('1e2');await p.getByRole('button',{name:'Review entered details'}).click();
    await p.getByRole('alert').waitFor();assert.equal(s.posts.length,0);
    await fill(p);assert.equal(s.posts.length,0);
    const confirm=p.getByRole('button',{name:'Confirm review and process refund'});assert.equal(await confirm.isEnabled(),false);
    await p.getByRole('checkbox').check();
    await confirm.evaluate(el=>{el.click();el.click();});
    await p.getByText('Provider pending',{exact:true}).first().waitFor();
    assert.equal(s.posts.length,1);assert.deepEqual(s.posts[0].payload,{reviewed_net_loss_pence:5000,review_reference:'synthetic-evidence-001'});
    assert.equal(await p.getByRole('button',{name:'Confirm review and process refund'}).count(),0);
  });
  await test('pending reconciliation uses existing status-only action',async(p,s)=>{
    await select(p);await p.getByRole('button',{name:'Check provider status — no new refund'}).click();
    await p.getByText('Provider confirmed',{exact:true}).first().waitFor();
    assert.equal(s.posts.length,1);assert.ok(s.posts[0].path.endsWith('/reconcile/'));assert.deepEqual(s.posts[0].payload,{});
    assert.equal(await p.getByRole('button',{name:'Review entered details'}).count(),0);
  },s=>state(s.details[0]));
  await test('uncertain POST never automatically retries',async(p,s)=>{
    await select(p);await fill(p);await p.getByRole('checkbox').check();await p.getByRole('button',{name:'Confirm review and process refund'}).click();
    await p.getByText(/Review submission is locked for this visit/).waitFor();
    await p.getByRole('button',{name:'Refresh saved status'}).click();await p.getByRole('heading',{name:'ACT-000041'}).waitFor();
    assert.equal(s.posts.length,1);assert.equal(await p.getByRole('button',{name:'Review entered details'}).count(),0);
  },s=>s.uncertain=true);
  await test('unknown accepted terms remain read-only',async(p,s)=>{
    await select(p);await waitText(p,'Unknown — support review required');
    assert.equal(await p.getByRole('button',{name:'Review entered details'}).count(),0);assert.equal(s.posts.length,0);
  },s=>{s.details[0].terms=null;s.details[0].terms_evidence='unknown';s.details[0].captured_pence=null;s.details[0].actions={review:false,reconcile:false,reason:'Historic accepted terms need support review.'};});
  await test('permission failure clears data and exposes no actions',async(p,s)=>{
    await p.getByRole('alert').waitFor();assert.equal(await p.getByRole('button',{name:/ACT-0000/}).count(),0);
    assert.equal(s.posts.length,0);await p.getByText(/An authorised staff session/).waitFor();
  },s=>s.denied=true);
  await test('late response cannot replace another selected case',async(p,s)=>{
    await p.getByRole('button',{name:/ACT-000041/}).click();await p.getByRole('button',{name:/ACT-000042/}).click();
    await p.getByRole('heading',{name:'ACT-000042'}).waitFor();await p.waitForTimeout(400);
    assert.equal(await p.getByRole('heading',{name:'ACT-000041'}).count(),0);assert.equal(s.posts.length,0);
  },s=>s.slowFirst=true);
  await test('empty queue is not mistaken for a successful refund',async(p,s)=>{
    await p.getByText(/No managed cancellation cases found/).waitFor();assert.equal(s.posts.length,0);
    assert.equal(await p.getByRole('button',{name:'Review entered details'}).count(),0);
  },s=>s.empty=true);
  await browser.close();
 }
 fs.writeFileSync(path.join(out,'RESULT.txt'),`Source: ${process.env.GITHUB_SHA||'local'}\n${results.join('\n')}\n${results.length} focused browser cases PASSED; mocked API only; no deployment.\n`);
 console.log(`${results.length} focused browser cases PASSED`);
})().catch(err=>{fs.writeFileSync(path.join(out,'RESULT.txt'),results.join('\n')+'\nFAILED: '+err.stack);console.error(err);process.exitCode=1;}).finally(async()=>{await Promise.allSettled(browsers.map(browser=>browser.close()));server.closeAllConnections();server.close();});
