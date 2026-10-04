# ACT vehicle-class rename migration — 2026-10-04

**Draft only. Not migrated on production, not merged, not deployed.**

## Approved class names

| Immutable code | Previous name | New professional name |
| --- | --- | --- |
| `comfort` | Standard PHV | Comfort Class |
| `comfort_xl` | 7 Seaters PHV | Comfort XL |
| `executive` | Luxury | Executive Class |
| `executive_xl` | Luxury Van | Executive XL |
| `first_class` | VIP Business PHV | First Class |

Arabic display names are migrated/localized as فئة الراحة، فئة الراحة XL، الفئة التنفيذية، الفئة التنفيذية XL، الدرجة الأولى.

## Architecture change

`VehicleType.code` is now the immutable machine identifier. Pricing, seeding and exact onboarding mappings use the code rather than `name_en`. Display names can therefore be edited in future without breaking fare lookup.

The migration adds the nullable code first, populates existing rows, renames the five known ACT rows, preserves unknown/custom rows with a unique `legacy_<pk>` code instead of guessing their meaning, then makes code non-null and unique. If duplicate old/new ACT class rows exist, the unique-code constraint intentionally causes migration failure rather than silently merge/delete business data.

Legacy and new display names remain accepted by the pricing compatibility resolver during transition. This preserves old tests/callers while production code has been moved to codes.

## Pricing safety

The numeric legacy pricing table is unchanged. Only its keys changed from editable names to immutable codes. Booking quote, trip creation and payment-authoritative pricing now pass `VehicleType.code`. Dynamic pricing resolves `VehicleType` by code; existing `PricingTier` foreign keys remain attached to the same rows when names are migrated.

Stripe metadata keeps the human-readable `car_type` and adds `car_type_code` for stable machine identification.

## Customer/operational surfaces updated in this draft

- Booking quote API includes vehicle code.
- Vehicle API serializer includes code.
- Booking frontend carries code and localized class names.
- English/Arabic and pending multilingual runtime class labels updated.
- Static frontend vehicle constants updated.
- Heathrow, Gatwick, Stansted, Luton and London City airport pages use the new class names.
- Driver application display labels use Comfort Class / Comfort XL while preserving existing submitted enum values. General `van_transporter` and `other` onboarding categories are deliberately not guessed as Executive XL/First Class.
- Admin trip and earnings payloads expose code alongside display names.
- Emails/PDFs/admin fields that read `VehicleType.name_en/name_ar` naturally receive the renamed database values after migration.

## Deliberately not included

- No representative Mercedes/BMW model claim or new vehicle image has been published yet.
- No per-class luggage capacities have been invented; the model still lacks approved per-class luggage capacity.
- No pricing rates/formula were changed; the separate distance-band monotonicity issue remains open.
- Historical stored PDFs/emails are not rewritten.
- Driver onboarding stored enum values are not renamed because doing so would unnecessarily break existing applications; only their user-facing labels/exact class resolution changed.

## Required pre-deployment checks

1. Back up the production database.
2. Query current VehicleType rows and confirm there is exactly one intended row for each of the five old/new classes; review all custom rows.
3. Verify current pricing feature flag and PricingTier foreign keys.
4. Run `python manage.py makemigrations --check` and `python manage.py migrate --plan`.
5. Run backend pricing/trip/payment/driver-onboarding tests including `apps.vehicle.tests.test_vehicle_class_codes`.
6. Run frontend build plus vehicle rename/selection tests.
7. On an isolated test database, run migration and compare pre/post quotes for all five classes at representative distances/airport directions. Prices must be identical for identical inputs.
8. Verify quote -> vehicle selection -> payment initiation -> booking -> email/PDF/admin displays the new name and stable code where applicable.
9. Only after evidence review should migration/deployment be approved.

Rollback must be tested before production. The migration supplies reverse names for the five ACT codes, but any deployment rollback must consider application-code/database-schema compatibility and must not be improvised on live data.
