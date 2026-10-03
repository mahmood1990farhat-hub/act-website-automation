require('../scripts/check-booking-language.cjs');
const assert = require('node:assert/strict');
const {getInstructionFile}=require('../src/lib/api/fetchInstructionFile.ts');
const {documentText}=require('../src/lib/document-text.ts');
process.env.NEXT_PUBLIC_API_BASE_URL='https://offline.example.invalid';
(async()=>{
  const locales=['en','ar','fr','de','es','tr','zh-CN'];
  for(const locale of locales){
    const files=locales.map(language=>({language,file_type:'FAQ',file_url:`/${language}.pdf`,updated_at:'2026-10-01'}));
    files.push({file_type:'FAQ',file_url:'/legacy.pdf',updated_at:'2099-01-01'});
    files.push({language:locale,file_type:'PRIVACY_POLICY',file_url:'/wrong-type.pdf',updated_at:'2099-01-01'});
    global.fetch=async url=>{ assert.equal(new URL(url).searchParams.get('locale'),locale);return {ok:true,json:async()=>({success:true,data:{instruction_files:files}})};};
    assert.equal((await getInstructionFile('FAQ',locale)).file_url,`/${locale}.pdf`);
    files.splice(files.findIndex(f=>f.language===locale&&f.file_type==='FAQ'),1);
    assert.equal(await getInstructionFile('FAQ',locale),null,'Never return another language or legacy file');
    for(const key of ['open','download','unavailable'])assert(documentText(locale,key));
  }
  console.log('PASS: exact language/type selection, missing-language fallback, legacy rejection and seven-language document controls');
})().catch(e=>{console.error(e);process.exitCode=1;});
