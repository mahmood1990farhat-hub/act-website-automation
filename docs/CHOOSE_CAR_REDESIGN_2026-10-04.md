# Professional Choose a Car redesign — 2026-10-04

**Status: draft implementation on PR #71. Not merged or deployed.**

## Implemented

The vehicle-selection screen now presents each returned ACT class as a larger premium card with:
- professional renamed class name;
- existing ACT/backend vehicle image in a substantially larger image stage;
- code-based representative model/category line;
- backend-authoritative one-way GBP total;
- maximum passenger count from VehicleType;
- private-transfer indicator;
- explicit selected state and Continue action;
- keyboard-selectable radio semantics;
- a visible statement that vehicle images/model examples are representative and exact vehicles may vary.

Representative examples currently drafted:
- Comfort Class — Comfortable saloon or equivalent.
- Comfort XL — Spacious 7-seat MPV or equivalent.
- Executive Class — Mercedes-Benz E-Class / EQE or equivalent.
- Executive XL — Mercedes-Benz V-Class or equivalent.
- First Class — Mercedes-Benz S-Class / BMW i7 or equivalent.

The Executive and First Class examples reflect the owner's requested direction. Executive XL uses the proposed V-Class positioning. These are **class examples, not guaranteed models**.

## Image decision

The repository contains general ACT imagery and the booking API already returns each VehicleType's `icon_url`, but this audit did not establish ownership/licensing of manufacturer-specific Mercedes/BMW photographs. The redesign therefore continues to use ACT's configured vehicle image source and does not hotlink or copy manufacturer marketing images.

Before production, replace/confirm each VehicleType image with an ACT-owned, licensed, supplier-authorised, or purpose-created representative asset. Image alt text uses the ACT class name; the disclaimer prevents the image from being presented as a guaranteed exact vehicle.

## Claims deliberately excluded

- No luggage capacity is shown per class because approved per-class luggage data does not yet exist.
- No star rating, “Most Popular” badge, guaranteed Mercedes/BMW model, Wi-Fi/water/child-seat promise, or other unverified inclusion is shown.
- No price is calculated in the card; it displays the backend quote total.
- No numeric tariff or eligibility rule changed.

## Acceptance still required

Run frontend TypeScript/build and source regression guards, then browser-review desktop/tablet/mobile for image cropping, RTL, keyboard focus, card selection and Continue behavior. Test all five classes from a real test-backend quote after the vehicle-code migration is rehearsed. Confirm/replace the five class images before release.
