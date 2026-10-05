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


# Approved luggage combinations are expressed as (large, small) maxima.
# A request is suitable when it fits wholly within at least one approved pattern.
VEHICLE_LUGGAGE_PATTERNS = {
    "comfort": ((2, 2), (0, 4)),
    "comfort_xl": ((3, 3), (4, 0)),
    "executive": ((2, 2), (0, 4)),
    "executive_xl": ((5, 4), (6, 2)),
    "first_class": ((2, 2), (0, 4)),
}


def vehicle_accepts_luggage(vehicle_code, large_suitcases, small_suitcases):
    code = canonical_vehicle_code(vehicle_code)
    patterns = VEHICLE_LUGGAGE_PATTERNS.get(code)
    if not patterns:
        return False
    large = int(large_suitcases or 0)
    small = int(small_suitcases or 0)
    return any(
        large <= max_large and small <= max_small
        for max_large, max_small in patterns
    )


def luggage_patterns_for_vehicle(vehicle_code):
    return VEHICLE_LUGGAGE_PATTERNS.get(canonical_vehicle_code(vehicle_code), ())
