# ACT admin commission controls — 9 October 2026

## Scope and baseline

Extends the existing Earnings area, BaseDriver individual-share field, CommissionRule, DriverCommissionGroup, DriverCommissionMembership, and CommissionResolver. Baseline: main `fad7f738051ca09835d9e5508d5309b6c244750d`, merged PR #82. No replacement finance system, deployment, production migration, payment, message or n8n operation.

Three sections are implemented in the existing Earnings page: ACT Global Commissions; Driver Commission Exceptions with a table; Driver Commission Groups with create, add and release-member actions. The first dropdown represents all drivers still in the global category. Individual/group selectors use only eligible global drivers; editing an existing exception does not create another membership. Driver IDs distinguish identical names. Returning a driver to global is explicit. CSV export is labelled as an Excel-compatible export, not an independent editable source of rates.

The admin-only GET/POST contract is `/api/admin-panel/commission-management/`. Every command uses ACT's deduction percentage (0–100, up to two decimal places). Individual rates convert to the existing driver-share field using `100 - deduction`. No customer-facing or driver-facing API contract is changed.

Commands: `set_global`, `set_individual`, `clear_individual`, `create_group`, `set_group_rate`, `add_members`, `release_members`. Mutations require a current configuration revision and reason. Conflicting membership batches roll back entirely. Changed configurations use the existing Django admin LogEntry audit trail, including actor, reason, before and after. Passenger charges and completed ledgers are not edited.

## Safety and release status

This is a draft implementation, NOT a production-ready finance release. New writes default to disabled. `ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True` is used only by isolated tests; no production environment or settings file is changed to enable it. The page reports preview status and disables saving; the API enforces the same lock regardless of client controls. Existing admin commission endpoints are preserved, not silently relabelled as protected by this new gate.

Two release dependencies remain explicit:

1. Accepted-job payout snapshots: PR #82 tests preserve completed ledgers, not a driver's accepted-but-uncompleted offer. Completion currently resolves commission using current rates. Before enabling this management API, integrate an immutable driver offer/payout snapshot across acceptance, release/reassignment and completion, and verify their common transaction/locking order. The new unfinished-assigned-trip check is a supplementary refusal, not proof that acceptance/edit races are solved.
2. Global versus legacy vehicle rules: the existing resolver prefers vehicle rules over global defaults. This draft refuses a global save when active vehicle-specific rules exist rather than silently deleting or overriding them. Complete a reviewed transition to the user's global/individual/group policy, including inactive group membership behaviour and existing bookings, before release.

No initial commercial deduction percentage has been selected. If no global record exists, the UI labels the existing resolver fallback as a fallback, not an approved new rate. Bonuses, reimbursements, scheduled future rates, third-party settlement and payout execution are outside this slice. Group rates do not create company settlement accounts.

## Test evidence correction

Prior acceptance #330 passed its configured tests, but `.github/workflows/website-acceptance.yml` did not include `apps.earnings.tests.test_commission_groups`. The prior claim that those new tests had passed was not supported by that workflow. This slice makes the test directory importable and explicitly runs both that existing module and the new HTTP tests. It also executes the real TypeScript list/percentage/CSV helper and checks the Earnings integration; these helper assertions are not browser or live-device acceptance.

The new tests cover permissions, the default write lock, exclusive category lists, ACT-deduction/driver-share conversion, zero and 100 percent, group creation/member changes, all-or-nothing membership conflict, stale revisions, invalid input, audit records, legacy rule protection and refusal to change an affected unfinished assigned journey. Full candidate CI and a later admin browser preview must be read before marking the relevant checkpoint accepted. No repeat production bookings or real payouts are necessary for this slice.

## Handoff to ACT AI Automation / mobile development agent

GitHub is the shared handoff record. This development workstream owns the commission API, admin controls and release decisions. The automation agent may review the PR and CI and report missing coverage; it must not independently calculate authoritative rates, change memberships, initiate settlements or build a second dispatcher. Do not enable this API or disturb Driver v2 connector diagnostics. Driver/passenger apps continue using the shared backend; driver earnings privacy and offer snapshots must be completed before consuming any new finance contracts. No claim is made that this note sends a message to another ChatGPT conversation.
