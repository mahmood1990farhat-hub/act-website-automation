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

// Exercise the actual account and trip components with synthetic data. Network is
// forbidden here, so accidental requests fail instead of reaching any provider.
global.fetch = async () => { throw new Error('Network forbidden in language checks'); };
require.extensions['.css'] = () => {};
const { AppRouterContext } = require('next/dist/shared/lib/app-router-context.shared-runtime');
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const router = { push() {}, replace() {}, refresh() {}, back() {}, forward() {}, prefetch() {} };
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const flatten = (data, prefix = '', out = {}) => {
  if (data && typeof data === 'object') {
    for (const [key, value] of Object.entries(data)) flatten(value, prefix ? `${prefix}.${key}` : key, out);
  } else out[prefix] = data;
  return out;
};
const dictionary = (locale, section) => JSON.parse(fs.readFileSync(path.join(root, `src/dictionaries/${locale}/${section}.json`), 'utf8'));
const enAuth = dictionary('en', 'auth');
for (const key of ['CreateCaptainAccount', 'driverOnboarding', 'GetStartedCaptain', 'admin_login']) delete enAuth[key];
const enTrips = dictionary('en', 'tripsPassenger');
const escape = text => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');
const components = Object.fromEntries(['Login','SignUp','ChangePasswordForm','ChangeEmailForm','ChangePhoneForm'].map(name => [name, require(`../src/components/_components/auth/${name}.tsx`).default]));
const Trip = require('../src/components/_components/Trips/MyTripsCard.tsx').default;
const Pagination = require('../src/components/_components/Pagination.tsx').default;
for (const locale of ['en', 'ar', 'fr', 'de', 'es', 'tr', 'zh-CN']) {
  const auth = dictionary(locale, 'auth'), trips = dictionary(locale, 'tripsPassenger');
  if (!['en', 'ar'].includes(locale)) {
    for (const [actual, expected] of [[auth, enAuth], [trips, enTrips]]) {
      const a = flatten(actual), e = flatten(expected);
      assert.deepEqual(Object.keys(a).sort(), Object.keys(e).sort(), locale + ': complete customer dictionary');
      for (const key of Object.keys(e)) {
        assert.equal(typeof a[key], typeof e[key], locale + ': ' + key);
        if (typeof e[key] === 'string') {
          assert(a[key].trim() || !e[key].trim(), locale + ': blank ' + key);
          assert.deepEqual([...a[key].matchAll(/\{\w+\}/g)].map(x => x[0]), [...e[key].matchAll(/\{\w+\}/g)].map(x => x[0]), locale + ': tokens ' + key);
        }
        if (key.endsWith('.value')) assert.equal(a[key], e[key], locale + ': canonical trip status');
      }
    }
  }
  const render = element => renderToStaticMarkup(React.createElement(AppRouterContext.Provider, { value: router }, React.createElement(QueryClientProvider, { client: new QueryClient() }, element)));
  for (const [component, section, keys] of [
    ['Login','login',['title','passwordLabel','loginButton']],
    ['SignUp','signup',['createAccount','firstName','lastName','enterPhone']],
    ['ChangePasswordForm','ChangePassword',['title','oldPassword','password']],
    ['ChangeEmailForm','ChangeEmail',['title','emailLabel','sendCode']],
    ['ChangePhoneForm','ChangePhone',['title','phoneLabel','sendCode']],
  ]) {
    const html = render(React.createElement(components[component], { locale, trans: auth[section], setTap() {}, setTapAction() {}, setSevePhoneforOTP() {} }));
    for (const key of keys) assert(html.includes(escape(auth[section][key])), `${locale}:${component}:${key}`);
  }
  const html = render(React.createElement(Trip, { locale, trans: trips.deleteTrip, tripCardTrans: trips.tripCard, data: { id: 42, status: 'pending', trip_date: '2026-10-09', distance_miles: 15, expected_trip_duration_minutes: 40, guest_driver_name: '张伟 <Test>', guest_driver_phone: '+447700900000' } }));
  assert(html.includes(escape(trips.tripCard.statusLabels.pending)), locale + ': status label');
  assert(html.includes(accountText(locale, 'miles')), locale + ': distance units');
  assert(html.includes('张伟 &lt;Test&gt;'), locale + ': customer/provider text untouched and escaped');
  const pages = render(React.createElement(Pagination, { locale, currentPage: 1, totalPages: 3, onPageChange() {} }));
  assert(pages.includes(accountText(locale, 'next')), locale + ': pagination');
}
console.log('PASS: seven-language account/trip renders, customer dictionary completeness, canonical statuses, units, pagination and user data preservation');
