# Quote and vehicle eligibility audit — 2026-10-04

**Status: source audit + safe UI hardening on draft PR #71. No fare/tariff change, no deployment.**

## Confirmed implementation

- Quote endpoint validates trip data, gets route distance, and filters vehicle types by `max_passengers_count >= passengers_count`.
- `VehicleType` currently stores name, descriptions, icon, passenger capacity and display order. It has **no per-vehicle-type luggage-capacity fields**.
- Trip-level online validation caps the request at 7 passengers and 8 total suitcases. That is not the same as proving every returned vehicle can physically carry the selected luggage.
- The quote response's `total_cost` is the backend-calculated amount shown by Choose a Car. This audit does not introduce a frontend fare calculation.
- Pricing routes through `calculate_total_cost`. A database feature flag chooses either the legacy hardcoded table or dynamic PricingTier engine. The repository default for `use_dynamic_pricing` is false, but the live database value has not been verified in this audit.

## Safe fixes made

- Choose a Car now shows the selected **journey date**, not the browser's current date.
- Removed the hardcoded, unsupported `4.9` rating.
- Removed the unsupported automatic “Most Popular” badge.
- Vehicle selection no longer auto-advances after 300 ms; the passenger selects a vehicle, reviews the card, then explicitly presses Continue.
- Restored the existing disabled-vehicle environment configuration instead of forcing every returned vehicle enabled.
- Enlarged the existing vehicle image area and formats the backend total as GBP currency.
- Added a no-suitable-vehicle state for defensive rendering.
- Quote validation errors from safe 4xx responses can now be shown to the passenger (for example the 3-hour rule); raw 5xx/debug details remain hidden behind the generic calculation error.

## Material eligibility gap — luggage

The backend can currently prove passenger capacity but cannot prove per-class luggage capacity because that data does not exist on VehicleType. Do **not** advertise a specific luggage capacity or filter individual classes by luggage until approved capacities are defined and stored. The current 8-suitcase trip-level limit should not be presented as the capacity of every vehicle.

Recommended next data decision: define large/small suitcase capacity (or a tested equivalent capacity model) for each ACT class, then add backend fields/migration, admin editing, quote filtering and tests.

## Reproduced pricing-boundary risk — do not change tariff silently

The legacy pricing table selects one per-mile rate for the **entire journey** based on the distance band. Rates generally fall at each band. This means crossing a band can reduce the calculated fare even though distance increased.

Example from the current Standard PHV normal table, before airport fees/minimum-fare effects:
- 39.99 miles uses £2.82/mile -> base £112.77; with 20% = about £135.33.
- 40.00 miles moves to £2.67/mile -> base £106.80; with 20% = £128.16.
- The longer journey is therefore about £7.17 lower at that boundary before equal airport fees.

This reproduces the *type* of anomaly previously reported (a longer journey becoming cheaper), but does not claim these are the exact historical live quote values. Airport fees, peak rates, minimum fare, route distance and the live dynamic-pricing flag affect actual quotes.

The dynamic engine also applies a single selected tier rate to the whole distance; whether it has a live discontinuity depends on the database PricingTier values, which are not established here.

**No pricing formula or rates were changed in this audit.** Correcting monotonicity is a consequential pricing decision and needs an approved method plus regression examples before implementation.

## Professional class-name constraint

The legacy pricing dictionary keys depend on canonical backend names such as `Standard PHV`, `7 Seaters PHV`, `Luxury`, `Luxury Van` and `VIP Business PHV`. Renaming `VehicleType.name_en` directly could break legacy pricing lookup.

Professional customer-facing names should therefore initially be a **presentation mapping** (for example Comfort Class / Comfort XL / Executive Class / Executive XL / First Class) while canonical pricing identifiers remain stable, unless pricing is refactored to use immutable IDs/codes first.

## Acceptance still required

- Full frontend build/TypeScript/browser test.
- Real test-backend quote cases for 1–7 passengers and luggage boundaries.
- Verify the live/staging pricing feature flag and configured tiers before pricing acceptance.
- Regression matrix around every distance threshold, peak/off-peak and airport pickup/drop-off.
- Owner approval of luggage capacities, customer-facing class names and representative vehicle models/images before publishing those claims.
