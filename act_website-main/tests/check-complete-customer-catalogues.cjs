// Offline source and rendered component checks; never submits a booking or payment.
require('../scripts/check-booking-language.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const React=require('react'),{renderToStaticMarkup:render}=require('react-dom/server');
const {customerText}=require('../src/lib/customer-text.ts');
const {runtimeText,customerPaymentError}=require('../src/lib/customer-runtime.ts');
const {bookingText}=require('../src/components/_components/bookTaxi/booking-text.ts');
const {getArrivalGuidance,getDepartureGuidance}=require('../src/components/_components/bookTaxi/flight-guidance.ts');
const noop=()=>{};
const locales=['en','ar','fr','de','es','tr','zh-CN'];
const read=(locale,name)=>require(`../src/dictionaries/${locale}/${name}.json`);
function flatten(v,p='',out={}){if(v&&typeof v==='object')for(const[k,x]of Object.entries(v))flatten(x,p?`${p}.${k}`:k,out);else out[p]=v;return out;}
const protectedKey=k=>/\.(url|href|value|downloadFileName)$/.test(k)||/\.hour(_5)?$/.test(k);
for(const locale of locales){
 for(const name of ['home','complaints','lostProperty']){
  const en=flatten(read('en',name)),copy=flatten(read(locale,name));assert.deepEqual(Object.keys(copy).sort(),Object.keys(en).sort(),`${locale}/${name}: missing or extra keys`);
  for(const[k,v]of Object.entries(en)){
   assert.equal(typeof copy[k],typeof v,`${locale}/${name}/${k}`);
   if(typeof v==='string'){
    assert(copy[k].trim()||!v.trim(),`${locale}/${name}/${k}: empty`);
    assert.deepEqual([...copy[k].matchAll(/\{\w+\}/g)].map(x=>x[0]).sort(),[...v.matchAll(/\{\w+\}/g)].map(x=>x[0]).sort(),`${locale}/${name}/${k}: placeholders`);
    if(k.endsWith('.value')||k.endsWith('.downloadFileName'))assert.equal(copy[k],v,`${locale}/${name}/${k}: stored value changed`);
    if(locale!=='en'&&!protectedKey(k)&&copy[k]===v){
      assert(/^(Airport & City|Transfer|Transport for London \(TfL\)|ACT - 450 Bath Road Heathrow|Farhat Trading Solutions Ltd|Office 218|London|West Drayton|UB7 0EB|404|SMS|E-mail|E-Mail|Email|Date|Distance|Description|Type|Photo|Color|Brand|Total|App|Apps|Profil|Profile|Status|Name|message|Info@airportandcitytransfer.com|\+44.*)$/.test(v.trim()),`${locale}/${name}/${k}: unexpected English fallback: ${v}`);
    }
   }else if(!protectedKey(k)) assert.equal(copy[k],v);
  }
  if(name==='home'){
   assert.equal(read(locale,name).policy_and_terms.policy.elements.length,7);
   assert.equal(read(locale,name).policy_and_terms.terms.elements.length,18);
   assert.equal(read(locale,name).faqs.elements.length,10);
  }
 }
 for(const[key,value]of Object.entries(require('../src/dictionaries/customer-runtime.json').en)){
  const actual=runtimeText(locale,key);assert(actual.trim());assert.deepEqual([...actual.matchAll(/\{\w+\}/g)].map(x=>x[0]).sort(),[...value.matchAll(/\{\w+\}/g)].map(x=>x[0]).sort());
 }
 for(const code of ['card_declined','expired_card','incorrect_cvc','payment_intent_authentication_failure','new_provider_code'])assert(customerPaymentError(locale,{code}));
 assert.equal(customerPaymentError(locale,{code:'unknown'}),runtimeText(locale,'paymentUnknown'));
 for(const[name,props,label]of [
  ['PassengerDetails',{passengerDetails:{fullName:'Synthetic 客户',email:'test@example.invalid',countryCode:'+44 United Kingdom',mobileNumber:'7700900000'},setPassengerDetails:noop},'Passenger Details'],
  ['ChildInfantTravelInfo',{passengerCounts:{adults:1,children:1,infants:1},childInfantTravel:{infantSeatOption:'I will provide my own infant seats',childSeatOption:'I would like ACT to provide child seats'},setChildInfantTravel:noop},'Infant Seat Requirement'],
  ['FlightDetails',{flightDetails:{flightType:'arrival',flightNumber:'BA123',airline:'British Airways',landingTime:'10:00',departureTime:'',pickupSignName:'Synthetic 客户'},setFlightDetails:noop,pickupTime:'10:30',routePoints:[{type:'pickup',point:{airport_code:'LHR'}}],changePickupTime:noop},'Flight Details'],
 ]){
   const component=require(`../src/components/_components/bookTaxi/${name}.tsx`).default;
   const html=render(React.createElement(component,{locale,nextStep:noop,prevStep:noop,...props}));
   const escaped=render(bookingText(locale,label));assert(html.includes(escaped),`${locale}/${name}: title`);
   if(name==='PassengerDetails'){assert(html.includes('value="+44 United Kingdom"'));assert(html.includes('Synthetic 客户'));}
   if(name==='ChildInfantTravelInfo')assert(html.includes('value="I will provide my own infant seats"'));
 }
 for(const[name,key]of [['date-picker','selectDate'],['act-time-picker','selectTime']]){
   const mod=require(`../src/components/_components/dateAndTime/${name}.tsx`);const component=mod.DatePicker||mod.ActTimePicker;
   const html=render(React.createElement(component,{language:locale,isOpen:true,onClose:noop,onSelect:noop,selectedDate:new Date(2026,10,15),selectedTime:{hour:13,minute:30}}));
   assert(html.includes(render(runtimeText(locale,key))),`${locale}/${name}`);
 }
 assert(!getArrivalGuidance('10:30','10:00',locale).includes('{suggestedPickup}'));
 assert(!getDepartureGuidance('11:30','12:00',locale).includes('{windowStart}'));
 if(!['en','ar'].includes(locale)){
  const airports=read(locale,'airports');assert.equal(Object.keys(airports.pages).length,5);
  const Page=require('../src/components/_components/FrenchAirportPage.tsx').default;
  for(const slug of Object.keys(airports.pages)){const html=render(React.createElement(Page,{locale,slug}));assert(html.includes(`/${locale}#book-now`));assert(html.includes(`lang="${locale}"`));assert(!html.includes('{airport}'));}
 }
}
console.log('PASS: complete seven-language home/support schemas, 7 privacy/18 terms/10 FAQ sections, placeholders, controlled values, rendered booking/date/time controls, payment messages and 25 translated airport pages');
