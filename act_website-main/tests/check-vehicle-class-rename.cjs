const assert=require("node:assert/strict"),fs=require("node:fs");
const constants=fs.readFileSync("src/lib/constants/vehicleTypes.ts","utf8");
const i18n=fs.readFileSync("i18n.config.ts","utf8");
const runtime=JSON.parse(fs.readFileSync("src/dictionaries/customer-runtime.json","utf8"));
const expected=[
 ["comfort","Comfort Class"],["comfort_xl","Comfort XL"],["executive","Executive Class"],
 ["executive_xl","Executive XL"],["first_class","First Class"]
];
for(const [code,name] of expected){
 assert.ok(constants.includes(`code: "${code}"`),`missing stable code ${code}`);
 assert.ok(constants.includes(`name_en: "${name}"`),`missing professional name ${name}`);
 assert.ok(i18n.includes(code),`localization does not recognise code ${code}`);
}
assert.equal(runtime.en.standardVehicle,"Comfort Class");
assert.equal(runtime.en.sevenSeater,"Comfort XL");
assert.equal(runtime.en.luxuryVehicle,"Executive Class");
assert.equal(runtime.en.luxuryVan,"Executive XL");
assert.equal(runtime.en.executiveVehicle,"First Class");
console.log("PASS stable vehicle codes and professional frontend class names");
