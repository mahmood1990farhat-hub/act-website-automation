const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const source = fs.readFileSync('src/lib/commission-management.ts', 'utf8');
const moduleUnderTest = { exports: {} };
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
}).outputText, { exports: moduleUnderTest.exports, module: moduleUnderTest }, { timeout: 1000 });
const { commissionLists, validCommissionPercentage, commissionCsv } = moduleUnderTest.exports;

const data = {
  groups: [{ id: 9, name: 'DSS', company_percentage: '15.00', is_active: true }],
  drivers: [
    { id: 1, name: 'Global Driver', category: 'global', group_id: null, company_percentage: '20.00', driver_percentage: '80.00' },
    { id: 2, name: '=SUM(1,2)', category: 'individual', group_id: null, company_percentage: '25.00', driver_percentage: '75.00' },
    { id: 3, name: 'Group Driver', category: 'group', group_id: 9, company_percentage: '15.00', driver_percentage: '85.00' },
    { id: 4, name: 'Conflict Driver', category: 'conflict', group_id: 9, company_percentage: '10.00', driver_percentage: '90.00' },
  ],
};
const lists = commissionLists(data);
assert.equal(lists.global.length, 1);
assert.equal(lists.individual.length, 1);
assert.equal(lists.grouped.length, 1);
assert.equal(lists.conflicts.length, 1);
const ids = Object.values(lists).flat().map((driver) => driver.id);
assert.equal(new Set(ids).size, data.drivers.length);
assert.throws(() => commissionLists({ ...data, drivers: [...data.drivers, data.drivers[0]] }), /Duplicate driver/);

for (const value of ['0', '0.00', '10', '20.25', '99.99', '100', '100.00', ' 15 ']) {
  assert.equal(validCommissionPercentage(value), true, value);
}
for (const value of ['', '-1', '101', '100.01', '1.001', 'NaN', 'Infinity', '20%', '1e2']) {
  assert.equal(validCommissionPercentage(value), false, value);
}
const csv = commissionCsv(data);
assert.ok(csv.startsWith('\uFEFF'));
assert.equal(csv.split('\r\n').length, 6);
assert.ok(csv.includes('"\'=SUM(1,2)"'), 'Excel formulas in driver names must be escaped');
assert.ok(csv.includes('"DSS","15.00","85.00"'));
for (const name of ['+SUM(1,2)', '-1+1', '@SUM(1,2)', '\t=1', '  =1']) {
  assert.ok(commissionCsv({ ...data, drivers: [{ ...data.drivers[0], name }] }).includes('"\'' + name), 'Unsafe CSV prefix must be escaped');
}
const component = fs.readFileSync('src/components/_components/dashboard/CommissionManagement.tsx', 'utf8');
const wrapper = fs.readFileSync('src/components/_components/dashboard/EarningsWrapper.tsx', 'utf8');
for (const label of ['ACT Global Commissions', 'Driver Commission Exceptions', 'Driver Commission Groups']) assert.ok(component.includes(label));
assert.ok(component.includes('revision: data.revision'), 'Saves must carry the server configuration revision');
assert.ok(component.includes('!data.writes_enabled'), 'Preview mode must keep new write controls disabled');
assert.ok(component.includes('lists?.global'), 'Eligible choices must use the exclusive global list');
assert.ok(wrapper.includes('<CommissionManagement') && wrapper.includes('<Earnings '), 'Extend, do not replace, existing admin earnings');
console.log('PASS commission category partitions, 18 percentage cases, safe CSV export and admin integration wiring');
