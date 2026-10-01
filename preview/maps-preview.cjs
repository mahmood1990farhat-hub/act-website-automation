// Actual local builds, same viewport and Maps-blocked condition; no live services.
const {chromium} = require('/opt/browser-test/node_modules/playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const server = spawn(process.execPath,['node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3001'],{stdio:'inherit'});
let browser;
async function main(){
 const origin='http://127.0.0.1:3001';
 let ready=false;
 for(let i=0;i<45;i++){try{if((await fetch(origin+'/en')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,1000));}
 if(!ready)throw Error('Local server unavailable');
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:1280,height:850},deviceScaleFactor:1,serviceWorkers:'block',locale:'en-GB'});
 await context.route('**/*',route=>{
  const url=new URL(route.request().url());
  if(url.origin!==origin||url.pathname.startsWith('/api/')||route.request().method()!=='GET')return route.abort();
  return route.continue();
 });
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 fs.mkdirSync('/tmp/maps-preview',{recursive:true});
 for(const [name,path] of [['airport','/en/heathrow-airport-transfer'],['home','/en']]){
  await page.goto(origin+path,{waitUntil:'networkidle'});
  await page.screenshot({path:`/tmp/maps-preview/${name}.png`,fullPage:false});
  console.log('Captured',path);
 }
 fs.writeFileSync('/tmp/maps-preview/conditions.json',JSON.stringify({viewport:'1280x850',externalNetwork:'blocked',maps:'unavailable',source:process.env.PREVIEW_SOURCE,errors},null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
