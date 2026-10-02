// Render production components without submitting accounts, OTPs or emails.
require('../scripts/check-booking-language.cjs');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { accountText } = require('../src/lib/customer-account-text.ts');
const Forgot = require('../src/components/_components/auth/ForgotPasswordForm.tsx').default;
const Reset = require('../src/components/_components/auth/ResetPasswordForm.tsx').default;
for (const locale of ['en', 'ar', 'fr', 'de', 'es', 'tr', 'zh-CN']) {
  const props = { locale, trans: { title: 'Test', desc: 'Test', description: 'Test', sendOtpButton: 'Test' }, setTap: () => {} };
  const html = renderToStaticMarkup(React.createElement(Reset, props));
  for (const key of ['otp', 'resetPassword', 'newPassword']) assert(html.includes(accountText(locale, key)), locale + ': ' + key);
  assert(html.includes('inputMode="numeric"'));
  const forgot = renderToStaticMarkup(React.createElement(Forgot, props));
  assert(forgot.includes(accountText(locale, 'email')));
}
console.log('PASS: seven-language password reset/request-code components; no submissions');
