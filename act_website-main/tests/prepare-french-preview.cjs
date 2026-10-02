// TEST IMAGE ONLY. No environment switch exists in application routing.
const fs = require('node:fs');
const assert = require('node:assert/strict');
assert.equal(process.env.ACT_TEST_FRENCH_PREVIEW, '1');
let config = fs.readFileSync('i18n.config.ts', 'utf8');
assert.ok(config.includes('fr: { label: "Français", direction: "ltr", enabled: false }'));
config = config.replace('fr: { label: "Français", direction: "ltr", enabled: false }', 'fr: { label: "Français", direction: "ltr", enabled: true }');
const guard = '(value === Languages.ENGLISH || value === Languages.ARABIC)';
assert.ok(config.includes(guard));
config = config.replace(guard, '(value === Languages.ENGLISH || value === Languages.ARABIC || value === "fr")');
fs.writeFileSync('i18n.config.ts', config);
console.log('French enabled only in disposable test image; no host ports or production configuration changed');
