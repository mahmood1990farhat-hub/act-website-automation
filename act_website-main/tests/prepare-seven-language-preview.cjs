// Creates a disposable all-language preview. Never changes the repository registry.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const root=path.resolve(__dirname,'..');
const out=fs.mkdtempSync(path.join(os.tmpdir(),'act-seven-preview-'));
fs.cpSync(root,out,{recursive:true,filter:source=>!['node_modules','.next','.git'].includes(path.basename(source))&&!source.endsWith('.tsbuildinfo')});
fs.symlinkSync(path.join(root,'node_modules'),path.join(out,'node_modules'),'dir');
const config=path.join(out,'i18n.config.ts');
const original=fs.readFileSync(config,'utf8');
const test=original.replaceAll('enabled: false','enabled: true').replace('(value === Languages.ENGLISH || value === Languages.ARABIC) && localeRegistry[value].enabled','isSupportedLocale(value) && localeRegistry[value].enabled');
if(test===original)throw Error('Preview registry contract changed');
fs.writeFileSync(config,test);
console.log(out);
