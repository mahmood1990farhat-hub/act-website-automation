def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _clean(value, default="Not provided"):
    if value is None:
        return default
    value = str(value).strip()
    return value or default


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _yes_no(value):
    if isinstance(value, str):
        return "Yes" if value.strip().lower() in {"true", "yes", "1", "on"} else "No"
    return "Yes" if bool(value) else "No"


def _format_extra_services(extra_services):
    services = _as_list(extra_services)
    labels = []
    for service in services:
        if isinstance(service, dict):
            label = service.get("service_name") or service.get("name") or service.get("label")
        else:
            label = service
        label = str(label).strip() if label is not None else ""
        if label:
            labels.append(label)
    return ", ".join(labels) if labels else "None"


def format_booking_details_for_email(trip):
    details = _as_dict(getattr(trip, "booking_details", {}) or {})

    passenger_counts = _as_dict(details.get("passenger_counts"))
    adults = _to_int(passenger_counts.get("adults"))
    children = _to_int(passenger_counts.get("children"))
    infants = _to_int(passenger_counts.get("infants"))
    total = _to_int(
        passenger_counts.get("total") or getattr(trip, "passengers_count", None)
    )

    flight_details = _as_dict(details.get("flight_details"))
    flight_type = _clean(flight_details.get("flight_type"), "").lower()
    if flight_type == "arrival":
        flight_type_label = "Arrival"
        flight_time_label = "Landing Time"
        flight_time = _clean(flight_details.get("landing_time"))
    elif flight_type == "departure":
        flight_type_label = "Departure"
        flight_time_label = "Departure Time"
        flight_time = _clean(flight_details.get("departure_time"))
    else:
        flight_type_label = "Not applicable"
        flight_time_label = "Time"
        flight_time = "Not applicable"

    child_infant = _as_dict(details.get("child_infant_travel"))
    infant_seat = _clean(child_infant.get("infant_seat_option"), "")
    child_seat = _clean(child_infant.get("child_seat_option"), "")

    additional = _as_dict(details.get("additional_requirements"))

    return {
        "passenger_counts": {
            "adults": adults,
            "children": children,
            "infants": infants,
            "total": total,
        },
        "flight_details": {
            "type": flight_type_label,
            "flight_number": _clean(flight_details.get("flight_number"), "Not applicable"),
            "airline": _clean(flight_details.get("airline"), "Not applicable"),
            "time_label": flight_time_label,
            "time": flight_time,
            "pickup_sign_name": _clean(flight_details.get("pickup_sign_name"), "Not applicable"),
        },
        "child_infant_travel": {
            "infant_seat_option": infant_seat or ("Not required" if not infants else "Not selected"),
            "child_seat_option": child_seat or ("Not required" if not children else "Not selected"),
        },
        "additional_requirements": {
            "meet_and_greet": _yes_no(additional.get("meet_and_greet")),
            "foldable_wheelchair": _yes_no(additional.get("foldable_wheelchair")),
            "notes_to_driver": _clean(additional.get("notes_to_driver"), "None"),
        },
        "extra_services": _format_extra_services(details.get("extra_services")),
    }
