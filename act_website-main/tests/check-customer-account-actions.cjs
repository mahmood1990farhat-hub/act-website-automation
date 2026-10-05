// Execute production handlers with only external effects replaced. No accounts,
// OTPs, cancellations, messages or network calls are made by these checks.
require('../scripts/check-booking-language.cjs');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const { accountText } = require('../src/lib/customer-account-text.ts');
function handler(file, name, env) {
  const source = fs.readFileSync(path.join(__dirname, '..', 'src/components/_components', file), 'utf8');
  const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let expression;
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(ast) === name) expression = node.initializer.getText(ast);
    ts.forEachChild(node, visit);
  }
  visit(ast);
  assert(expression, name);
  return vm.runInNewContext(ts.transpileModule(`(${expression})`, {compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText, env);
}
async function main() {
  for (const locale of ['en','ar','fr','de','es','tr','zh-CN']) {
    for (const fail of [false, true]) {
      const requests = [], notices = [], invalidations = [], pending = [], closed = [];
      const env = { locale, accountText, data: {id:42}, token:'synthetic-token', cancelling:false,
        postData: async options => { requests.push(options); if(fail) throw Error('offline simulated error'); return {}; },
        toast: {success:s=>notices.push(['success',s]),error:s=>notices.push(['error',s])},
        queryClient: {invalidateQueries: async key=>invalidations.push(key)},
        setCancelling:s=>pending.push(s), setOpenModal:s=>closed.push(s),
      };
      await handler('Trips/MyTripsCard.tsx','CancelTrip',env)();
      assert.equal(requests.length,1);
      assert.equal(requests[0].queryParams.locale,locale);
      assert.equal(requests[0].noToast,true);
      assert.equal(requests[0].endpoint,'/api/trips/42/cancel/');
      assert.deepEqual(pending,[true,false]);
      assert.equal(notices[0][1],accountText(locale, fail ? 'cancelTripFailed':'cancelTripSuccess'));
      assert.equal(closed.length,fail?0:1);
      assert.equal(invalidations.length,fail?0:2);
      for (const [component, field, value] of [['ChangeEmailForm','email','synthetic@example.invalid'],['ChangePhoneForm','phone_number','+447700900000']]) {
        requests.length=0; notices.length=0;
        const steps=[], cookieWrites=[];
        const changeEnv = {...env, otp:['1','2','3','4','5','6'], trans:{}, requestedEmail:value, requestedPhone:value, isLoading:false,
          onSuccess:()=>steps.push('success'),setStep:s=>steps.push(s),setRequestedEmail(){},setRequestedPhone(){},
          setCookie:(...a)=>cookieWrites.push(a),setPhone(){},setOtp(){},setTimeLeft(){},setIsLoading(){}};
        await handler(`auth/${component}.tsx`,'onConfirmChange',changeEnv)();
        assert.equal(requests[0].queryParams.locale,locale);
        assert.equal(requests[0].body.target,field==='email'?'email':'phone');
        assert.equal(requests[0].body.code,'123456');
        assert.equal(requests[0].noToast,true);
        assert.equal(cookieWrites.length,fail?0:1);
        assert.equal(steps.includes('success'),!fail);
        if(fail) assert.equal(notices[0][1],accountText(locale,'changeFailed'));
      }
    }
  }
  console.log('PASS: seven-language cancellation and email/phone confirmation success/failure handlers; request locale, canonical payloads and no premature success');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
