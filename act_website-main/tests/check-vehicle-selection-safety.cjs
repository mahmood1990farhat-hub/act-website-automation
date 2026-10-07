const assert=require("node:assert/strict"),fs=require("node:fs");
const car=fs.readFileSync("src/components/_components/bookTaxi/ChooseCar.tsx","utf8");
const index=fs.readFileSync("src/components/_components/bookTaxi/index.tsx","utf8");
assert.ok(car.includes("tripDate: string;"),"vehicle screen must receive journey date");
assert.ok(index.includes("tripDate={formDetails.date}"),"booking flow must pass journey date");
assert.ok(!car.includes("<span>4.9</span>"),"unsupported hardcoded rating must not render");
assert.ok(!car.includes("setTimeout(() =>"),"vehicle selection must not auto-advance");
assert.ok(car.includes("disabledCarIndices.includes(index)"),"disabled vehicle configuration must be respected");
assert.ok(car.includes('style: "currency"') && car.includes('currency: "GBP"'),"backend total must be formatted as GBP");
assert.ok(car.includes('customerText(locale, "No suitable vehicle is available for this journey online.")'),"defensive empty state missing");
console.log("PASS vehicle-selection safety/presentation regression guard");

for (const expected of [
  'role="radiogroup"',
  'role="radio"',
  'aria-checked={isSelected}',
  'runtimeText(locale, "representativeVehicle")',
  'runtimeText(locale, "vehicleMayVary")',
  'runtimeText(locale, "oneWayTotal")',
  'vehicleExample(locale, car.code)',
  'passengerCapacityLabel(locale, car.max_passengers_count)',
  'event.key === "Enter" || event.key === " "',
]) assert.ok(car.includes(expected), "missing professional/accessibility vehicle-card behavior: "+expected);

// Execute the existing presenter with the actual shared language catalogue.
// This is presentation-only: no API, payment, vehicle record or availability write.
const ts = require("typescript");
const vm = require("node:vm");
const copy = JSON.parse(fs.readFileSync("src/dictionaries/customer-runtime.json", "utf8"));
function loadPresenterModule(filename, dependencies) {
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, esModuleInterop: true },
  }).outputText;
  vm.runInNewContext(code, {
    module, exports: module.exports,
    require: (name) => {
      assert.ok(Object.prototype.hasOwnProperty.call(dependencies, name), "Unexpected presenter dependency: " + name);
      return dependencies[name];
    },
  }, { filename, timeout: 1000 });
  return module.exports;
}
const runtime = loadPresenterModule("src/lib/customer-runtime.ts", { "../dictionaries/customer-runtime.json": copy });
const { vehicleExample } = loadPresenterModule("src/lib/vehicle-presentation.ts", { "@/lib/customer-runtime": runtime });
const approved = {
  en: ["Mercedes-Benz EQE / E-Class / C-Class or equivalent", "Mercedes-Benz S-Class / BMW i7 / Volkswagen ID.7 or equivalent"],
  ar: ["مرسيدس-بنز EQE / E-Class / C-Class أو ما يعادلها", "مرسيدس-بنز S-Class / BMW i7 / فولكسفاغن ID.7 أو ما يعادلها"],
  fr: ["Mercedes-Benz EQE / Classe E / Classe C ou équivalent", "Mercedes-Benz Classe S / BMW i7 / Volkswagen ID.7 ou équivalent"],
  de: ["Mercedes-Benz EQE / E-Klasse / C-Klasse oder vergleichbar", "Mercedes-Benz S-Klasse / BMW i7 / Volkswagen ID.7 oder vergleichbar"],
  es: ["Mercedes-Benz EQE / Clase E / Clase C o equivalente", "Mercedes-Benz Clase S / BMW i7 / Volkswagen ID.7 o equivalente"],
  tr: ["Mercedes-Benz EQE / E-Serisi / C-Serisi veya dengi", "Mercedes-Benz S-Serisi / BMW i7 / Volkswagen ID.7 veya dengi"],
  "zh-CN": ["梅赛德斯-奔驰 EQE / E级 / C级 或同等级车型", "梅赛德斯-奔驰 S级 / BMW i7 / 大众 ID.7 或同等级车型"],
};
assert.deepEqual(Object.keys(copy).sort(), Object.keys(approved).sort(), "Every supported language must have approved examples");
for (const [locale, [executive, first]] of Object.entries(approved)) {
  assert.equal(vehicleExample(locale, "executive"), executive, locale + ": Executive examples must use the stable executive code");
  assert.equal(vehicleExample(locale, "first_class"), first, locale + ": First Class examples must use the stable first_class code");
  for (const [code, key] of [["comfort", "vehicleExampleComfort"], ["comfort_xl", "vehicleExampleComfortXl"], ["executive_xl", "vehicleExampleExecutiveXl"]]) {
    assert.equal(vehicleExample(locale, code), copy[locale][key], locale + ": preserve unrelated class " + code);
  }
  assert.ok(copy[locale].vehicleMayVary, locale + ": keep the representative-vehicle disclaimer");
  assert.equal(vehicleExample(locale, "unknown_class"), "", "Unknown vehicle codes must not acquire a model example");
}
assert.equal(vehicleExample("unknown-locale", "first_class"), approved.en[1], "Keep the existing English fallback");
console.log("PASS approved First/Executive model examples in all 7 languages; existing class mapping, fallback and disclaimer preserved");
