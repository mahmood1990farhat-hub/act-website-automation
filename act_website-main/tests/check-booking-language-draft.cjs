require('../scripts/check-booking-language.cjs');
const assert=require('node:assert/strict');
const {sanitizeBookingDraft,saveLanguageDraft,takeLanguageDraft,clearLanguageDraft}=require('../src/lib/booking-language-draft.ts');
const {languageSwitchText}=require('../src/lib/language-switch-text.ts');
const map=new Map();
const storage={setItem:(k,v)=>map.set(k,v),getItem:k=>map.get(k)||null,removeItem:k=>map.delete(k)};
const sample={
 routePoints:[{id:1,type:'pickup',point:{id:3,name_en:'Heathrow',airport_code:'LHR',coordinates:{lat:51.47,lng:-0.45},token:'secret'}},{id:2,type:'dropoff',point:{place_id:'synthetic-place',description:'张伟 <Home>',coordinates:{lat:51.5,lng:0}}}],
 formDetails:{date:'2026-10-10',time:'13:30',smallSuitcase:1,largeSuitcase:2,adults:2,children:1,infants:0,numberOfPassengers:3},
 passengerDetails:{fullName:'ليلى Test',email:'synthetic@example.invalid',countryCode:'+44 United Kingdom',mobileNumber:'7700900000',password:'secret'},
 childInfantTravel:{infantSeatOption:'',childSeatOption:'I would like ACT to provide child seats'},
 flightDetails:{flightType:'arrival',flightNumber:'BA123',airline:'British Airways',landingTime:'12:00',departureTime:'',pickupSignName:'ليلى Test'},
 additionalRequirements:{notesToDriver:'Need help'},clientSecret:'secret',paymentTotal:100,SelectedCar:{id:5},step:8,
};
const clean=sanitizeBookingDraft(sample);
assert(!JSON.stringify(clean).includes('secret'));
assert(!('SelectedCar' in clean));assert(!('paymentTotal' in clean));assert(!('step' in clean));
for(const destination of ['en','ar','fr','de','es','tr','zh-CN']){
 saveLanguageDraft(storage,sample,destination,1000);
 const restored=takeLanguageDraft(storage,destination,2000);
 assert.deepEqual(restored,clean);
 assert.equal(restored.passengerDetails.fullName,'ليلى Test');
 assert.equal(restored.routePoints[1].point.description,'张伟 <Home>');
 assert.equal(restored.childInfantTravel.childSeatOption,sample.childInfantTravel.childSeatOption);
 assert.equal(takeLanguageDraft(storage,destination,2000),null,'consumed only once');
 for(const key of ['choose','restored','payment','failed']) assert(languageSwitchText(destination,key));
}
saveLanguageDraft(storage,sample,'de',1000);assert.equal(takeLanguageDraft(storage,'fr',2000),null);
saveLanguageDraft(storage,sample,'de',1000);assert.equal(takeLanguageDraft(storage,'de',400000),null);
saveLanguageDraft(storage,sample,'de',1000);clearLanguageDraft(storage);assert.equal(map.size,0);
assert.throws(()=>sanitizeBookingDraft({...sample,formDetails:{...sample.formDetails,adults:-1}}));
assert.throws(()=>saveLanguageDraft({setItem(){throw Error('Storage blocked')}},sample,'de'));
console.log('PASS: seven-language one-time draft transfer, expiry, destination isolation, canonical/customer values and payment/secret exclusion');
