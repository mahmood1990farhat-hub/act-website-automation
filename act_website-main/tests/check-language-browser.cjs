const {chromium}=require('/opt/browser-test/node_modules/playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const origin='http://127.0.0.1:3001';
const server=spawn(process.execPath,['node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3001'],{stdio:'inherit'});
let browser;
async function main(){
 for(let i=0;i<45;i++){try{if((await fetch(origin+'/en')).ok)break;}catch{}await new Promise(r=>setTimeout(r,1000));}
 for(const locale of ['zh-CN','tr','es','fr','de'])assert.equal((await fetch(origin+'/'+locale)).status,404);
 const sitemap=await (await fetch(origin+'/sitemap.xml')).text();
 for(const locale of ['zh-CN','tr','es','fr','de'])assert.ok(!sitemap.includes('.com/'+locale+'/'));
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:850},serviceWorkers:'block'});
  await context.route('**/*',r=>new URL(r.request().url()).origin===origin&&!r.request().url().includes('/api/')?r.continue():r.abort());
  const page=await context.newPage();
  for(const locale of ['en','ar']){
   await page.goto(origin+'/'+locale+'/about-us?source=language-check#contact-us',{waitUntil:'networkidle'});
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert.equal(await page.locator('html').getAttribute('dir'),locale==='ar'?'rtl':'ltr');
   if(width===390)await page.locator('button[aria-expanded]:visible').first().click();
   const label=locale==='ar'?'اختر اللغة':'Choose language';
   const button=page.getByRole('button',{name:label,exact:true}).filter({visible:true});
   await button.click();
   const options=page.locator('button[lang]:visible');assert.equal(await options.count(),2);
   const target=locale==='en'?'ar':'en';
   await page.locator('button[lang="'+target+'"]:visible').click();
   await page.waitForURL('**/'+target+'/about-us?source=language-check#contact-us');
   console.log('PASS switch preserves path/query/hash',width,locale);
  }
  await context.close();
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');});
