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
