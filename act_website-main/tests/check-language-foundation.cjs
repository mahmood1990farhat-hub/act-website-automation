const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
require.extensions['.ts'] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText,file);
const cfg = require('../i18n.config.ts');
const {mergeDictionary,missingTranslationKeys}=require('../src/lib/translation-fallback.ts');
assert.deepEqual(cfg.enabledLocales,['en','ar']);
for(const locale of ['zh-CN','tr','es','fr','de']) {
 assert.equal(cfg.isSupportedLocale(locale),true);
 assert.equal(cfg.isEnabledLocale(locale),false);
 assert.equal(cfg.directionFor(locale),'ltr');
 assert.equal(cfg.dictionaryLocale(locale),'en');
 assert.equal(cfg.localizedVehicleValue({name_en:'Standard',name_ar:'عادية'},'name',locale),'Standard');
}
assert.equal(cfg.directionFor('ar'),'rtl');
assert.equal(cfg.localeFromPath('/english'),undefined);
assert.equal(cfg.localeFromPath('/enough'),undefined);
assert.equal(cfg.localeFromPath('/ar/about-us'),'ar');
assert.equal(cfg.localizedPath('/en/about-us?x=1#contact-us','ar'),'/ar/about-us?x=1#contact-us');
assert.equal(cfg.localizedPath('/english','ar'),'/ar/english');
assert.equal(cfg.localizedPath('https://example.com/en','ar'),'https://example.com/en');
assert.equal(cfg.localizedPath('//example.com/en','ar'),'//example.com/en');
assert.deepEqual(cfg.publishedLocalesFor('heathrow-airport-transfer'),['en','ar']);
assert.deepEqual(cfg.publishedLocalesFor('unpublished'),[]);
assert.deepEqual(mergeDictionary({a:{x:'English',y:'Default'},z:[1]}, {a:{x:'عربي'},z:[2]}),{a:{x:'عربي',y:'Default'},z:[2]});
assert.deepEqual(missingTranslationKeys({a:{x:1,y:2}},{a:{x:3}}),['a.y']);
for(const section of ['home','auth','complaints','lostProperty','tripsPassenger','driver','dashboard']){
 const en=require('../src/dictionaries/en/'+section+'.json'),ar=require('../src/dictionaries/ar/'+section+'.json');
 const missing=missingTranslationKeys(en,ar);
 assert.deepEqual(missingTranslationKeys(en,mergeDictionary(en,ar)),[]);
 console.log('Dictionary fallback audit',section,JSON.stringify(missing));
}
const {NextRequest}=require('next/server');
const {middleware}=require('../src/middleware.ts');
function request(path,accept='fr',cookies='') {return new NextRequest('https://airportandcitytransfer.com'+path,{headers:{'accept-language':accept,cookie:cookies}});}
for(const language of ['zh-CN','tr','es','fr','de']){
 const response=middleware(request('/'+language+'/heathrow-airport-transfer'));
 assert.equal(response.status,404);assert.equal(response.headers.get('x-robots-tag'),'noindex');
}
assert.equal(new URL(middleware(request('/')).headers.get('location')).pathname,'/en');
assert.equal(new URL(middleware(request('/en/driver','ar')).headers.get('location')).pathname,'/en/auth');
assert.equal(new URL(middleware(request('/ar/dashboard','en')).headers.get('location')).pathname,'/ar/auth');
assert.equal(new URL(middleware(request('/en/driver','ar','userToken=synthetic; account_type=normal')).headers.get('location')).pathname,'/en/dashboard/overview');
assert.equal(middleware(request('/ar/driver/overview','en','userToken=synthetic; account_type=normal_driver; is_admin_verified=true')).status,200);
assert.equal(new URL(middleware(request('/en/dashboard','ar','userToken=synthetic; account_type=passenger')).headers.get('location')).pathname,'/en');
console.log('PASS language registry, hidden routes, fallback, exact paths and role redirects');
