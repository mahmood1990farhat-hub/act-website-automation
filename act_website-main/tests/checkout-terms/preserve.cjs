const fs=require('node:fs'),cp=require('node:child_process'),assert=require('node:assert/strict'),ts=require('typescript');
const BASE='fb93e5534de15e25e3b45f1935f6a61b25c672e8';
const before=p=>cp.execFileSync('git',['show',`${BASE}:act_website-main/${p}`],{encoding:'utf8'});
const after=p=>fs.readFileSync(p,'utf8');
const tokens=s=>{const scanner=ts.createScanner(ts.ScriptTarget.Latest,true,ts.LanguageVariant.JSX,s.trimEnd()),result=[];let kind;while((kind=scanner.scan())!==ts.SyntaxKind.EndOfFileToken)result.push([kind,scanner.getTokenText()]);return result;};
const path='src/components/_components/bookTaxi/ConfirmFlightDetails.tsx';
const original=before(path);let restored=after(path);
const edits=[
 ['import { CheckoutTermsConsent, checkoutTermsText, useCheckoutTerms } from "./CheckoutTerms";\n',''],
 ['  const terms = useCheckoutTerms(locale, data, token);\n',''],
 ['    if (isLoading || !terms.ready) return;\n',''],
 ['const res = await terms.prepare(acknowledgement => postData<any>({','const res = await postData<any>({'],
 ['          ...(acknowledgement ? { booking_terms_acknowledgement: acknowledgement } : {}),\n',''],
 ['\t\t\t}));\n\t\t\tsetIsLoading(false);','\t\t\t});\n\t\t\tsetIsLoading(false);'],
 ['      if (!res) return;\n',''],
 ['\n          disabled={isLoading || terms.uncertain}\n','\n'],
 ['\n                  disabled={isLoading || terms.uncertain}\n','\n'],
 ['          <CheckoutTermsConsent gate={terms} locale={locale} disabled={isLoading} />\n',''],
 ['disabled={isLoading || !terms.ready}','disabled={isLoading}'],
];
for(const[a,b]of edits){assert.equal(restored.split(a).length-1,1,`Expected one scoped change: ${a}`);restored=restored.replace(a,b);}
const at=original.indexOf('className="flex items-center justify-center gap-1 max-w-xs sm:max-w-none"');
const start=original.indexOf('<span>',at),end=original.indexOf('</span>',start)+7;
restored=restored.replace('<span>{checkoutTermsText(locale, 10)}</span>',original.slice(start,end));
assert.deepEqual(tokens(restored),tokens(original),'Review details, pricing and payment payload must remain unchanged outside scoped consent edits');
const card='src/components/_components/stripe/CheckoutForm.tsx',a=before(card),b=after(card);
const segment=(s,start,end)=>s.slice(s.indexOf(start),s.indexOf(end,s.indexOf(start)));
assert.equal(segment(a,'  const fireBookingCompletedEvents','  const handleSubmit'),segment(b,'  const fireBookingCompletedEvents','  const handleSubmit'),'Preserve analytics and booking-status polling exactly');
assert.equal(segment(a,'    const card = elements.getElement','    } finally {'),segment(b,'    const card = elements.getElement','    } finally {'),'Preserve original Stripe confirmation and result handling exactly');
assert.equal(after('src/components/_components/bookTaxi/BookingFlow.tsx'),before('src/components/_components/bookTaxi/index.tsx'),'Original booking flow must be an exact move');
assert.match(after('src/components/_components/bookTaxi/index.tsx'),/<CheckoutTermsProvider><BookingFlow/);
console.log('PASS: original booking flow exact; review/payment payload preserved; Stripe confirmation, polling and analytics unchanged.');
