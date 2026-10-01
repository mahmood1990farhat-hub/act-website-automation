// Capture exact candidate at desktop/mobile sizes; external services blocked.
const {chromium}=require('/opt/browser-test/node_modules/playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const origin='http://127.0.0.1:3001';
const server=spawn(process.execPath,['node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3001'],{stdio:'inherit'});
let browser;
async function main(){
 for(let i=0;i<45;i++){try{if((await fetch(origin+'/en')).ok)break;}catch{}await new Promise(r=>setTimeout(r,1000));}
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 fs.mkdirSync('/tmp/approved-preview',{recursive:true});
 for(const [size,viewport] of [['desktop',{width:1280,height:850}],['mobile',{width:390,height:844}]]){
  const context=await browser.newContext({viewport,serviceWorkers:'block',deviceScaleFactor:1});
  await context.route('**/*',r=>{const u=new URL(r.request().url());return u.origin!==origin||u.pathname.startsWith('/api/')||r.request().method()!=='GET'?r.abort():r.continue();});
  const page=await context.newPage();
  for(const locale of ['en','ar']){
   await page.goto(origin+'/'+locale+'/heathrow-airport-transfer',{waitUntil:'networkidle'});
   await page.getByRole('heading',{level:1,name:locale==='ar'?'خدمة التوصيل من وإلى مطار هيثرو في لندن':'Heathrow Airport Transfer London',exact:true}).waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'No horizontal page overflow');
   if(locale==='ar'){
    const main=page.locator('main[lang="ar"]');
    assert.equal(await main.getAttribute('dir'),'rtl');
    assert.equal(await page.title(),'توصيل من وإلى مطار هيثرو في لندن | ACT');
    assert.equal(await main.locator('h3').count(),5);
    assert.equal(await main.locator('a[href="tel:+442081530303"]').count(),1);
   }
   await page.screenshot({path:`/tmp/approved-preview/${locale}-${size}.png`});
   await page.screenshot({path:`/tmp/approved-preview/${locale}-${size}-full.png`,fullPage:true});
   console.log('PASS screenshot/layout',locale,size);
  }
  await context.close();
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
