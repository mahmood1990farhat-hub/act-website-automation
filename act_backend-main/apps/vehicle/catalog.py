"""Canonical ACT vehicle-class identifiers and display names.

Pricing and integrations must depend on immutable codes, never editable customer-facing names.
"""

VEHICLE_CLASSES = {
    "comfort": {
        "name_en": "Comfort Class",
        "name_ar": "فئة الراحة",
        "legacy_names": ("Standard PHV",),
    },
    "comfort_xl": {
        "name_en": "Comfort XL",
        "name_ar": "فئة الراحة XL",
        "legacy_names": ("7 Seaters PHV",),
    },
    "executive": {
        "name_en": "Executive Class",
        "name_ar": "الفئة التنفيذية",
        "legacy_names": ("Luxury",),
    },
    "executive_xl": {
        "name_en": "Executive XL",
        "name_ar": "الفئة التنفيذية XL",
        "legacy_names": ("Luxury Van",),
    },
    "first_class": {
        "name_en": "First Class",
        "name_ar": "الدرجة الأولى",
        "legacy_names": ("VIP Business PHV",),
    },
}

LEGACY_NAME_TO_CODE = {
    legacy_name: code
    for code, config in VEHICLE_CLASSES.items()
    for legacy_name in config["legacy_names"]
}

DISPLAY_NAME_TO_CODE = {
    config["name_en"]: code for code, config in VEHICLE_CLASSES.items()
}


def canonical_vehicle_code(value):
    """Resolve a canonical code while tolerating old/new names during migration."""
    if not value:
        return value
    if value in VEHICLE_CLASSES:
        return value
    return LEGACY_NAME_TO_CODE.get(value) or DISPLAY_NAME_TO_CODE.get(value) or value


# Customer-facing luggage promises must be achievable for the booked occupancy.
# Patterns are (large, small) maxima; a request must fit wholly within one pattern.
VEHICLE_LUGGAGE_PATTERNS = {
    "comfort": ((2, 2), (0, 4)),
    # Comfort XL is handled by occupancy below because the third row consumes boot space.
    "comfort_xl": ((4, 2),),
    # Conservative saloon promise that remains safe when a hybrid/PHEV is dispatched.
    "executive": ((2, 0), (0, 3)),
    # Maximum capacity assumes a suitable long-wheelbase passenger van.
    "executive_xl": ((5, 4), (6, 2)),
    # Conservative S-Class/i7-class promise; avoids relying on a full-size non-hybrid boot.
    "first_class": ((2, 0), (0, 3)),
}


def luggage_patterns_for_vehicle(vehicle_code, passengers_count=None):
    code = canonical_vehicle_code(vehicle_code)
    if code == "comfort_xl" and passengers_count is not None:
        passengers = int(passengers_count or 0)
        if passengers >= 6:
            return ((1, 0), (0, 2))
    return VEHICLE_LUGGAGE_PATTERNS.get(code, ())


def vehicle_accepts_luggage(
    vehicle_code,
    large_suitcases,
    small_suitcases,
    passengers_count=None,
):
    patterns = luggage_patterns_for_vehicle(vehicle_code, passengers_count)
    if not patterns:
        return False
    large = int(large_suitcases or 0)
    small = int(small_suitcases or 0)
    return any(
        large <= max_large and small <= max_small
        for max_large, max_small in patterns
    )
