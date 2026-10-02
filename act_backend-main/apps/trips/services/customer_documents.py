"""Arabic customer documents. User-entered names, addresses and notes stay verbatim."""
from django.template.loader import render_to_string
from .booking_details_formatter import format_booking_details_for_email

AR_VALUES = {
    "Not provided": "غير مذكور", "Not applicable": "لا ينطبق", "Not required": "غير مطلوب",
    "Not selected": "لم يتم الاختيار", "None": "لا يوجد", "Yes": "نعم", "No": "لا",
    "Arrival": "وصول", "Departure": "مغادرة", "Landing Time": "وقت الوصول",
    "Departure Time": "وقت المغادرة", "Time": "الوقت", "N/A": "غير متوفر",
    "Private Transfer": "نقل خاص", "External Driver": "سائق خارجي", "Assigned Driver": "السائق المعيّن",
    "I will provide my own infant seats": "سأوفر مقاعد الرضع بنفسي",
    "I would like ACT to provide infant seats": "أرغب في أن توفر ACT مقاعد الرضع",
    "I understand ACT may not have infant seats available and wish to continue": "أفهم أن مقاعد الرضع قد لا تتوفر لدى ACT وأرغب في المتابعة",
    "I will provide my own child seats": "سأوفر مقاعد الأطفال بنفسي",
    "I would like ACT to provide child seats": "أرغب في أن توفر ACT مقاعد الأطفال",
    "I understand ACT may not have child seats available and wish to continue": "أفهم أن مقاعد الأطفال قد لا تتوفر لدى ACT وأرغب في المتابعة",
}
TITLES = {
    "booking": "تأكيد الحجز",
    "cancellation": "تأكيد إلغاء الحجز",
    "driver": "بيانات السائق",
    "driver_cancelled": "تحديث بشأن السائق المعيّن",
    "reassigned": "تعيين سائق جديد",
}
INTROS = {
    "booking": "شكرًا لاختيارك Airport & City Transfer. تم تأكيد رحلتك. يرجى مراجعة تفاصيل الحجز والاحتفاظ بهذا التأكيد.",
    "cancellation": "نؤكد إلغاء حجزك. تخضع أهلية الاسترداد للشروط المتفق عليها وقت الحجز. نبدأ رد أي مبلغ مستحق إلى وسيلة الدفع الأصلية خلال 5 أيام عمل من تأكيد المبلغ. وقد يستغرق البنك أو مزود الدفع وقتًا إضافيًا لإيداعه.",
    "driver": "فيما يلي بيانات السائق والمركبة المعيّنين لرحلتك.",
    "driver_cancelled": "اعتذر السائق المعيّن عن تنفيذ الرحلة. سيعمل فريقنا على تعيين سائق آخر. هذا إشعار بتغيير السائق وليس تأكيدًا لإلغاء الحجز.",
    "reassigned": "تم تعيين سائق جديد لرحلتك. يمكنك التواصل معه باستخدام رقم الهاتف أدناه.",
}
CONTACT = "لطلب إلغاء الحجز أو تعديله، أرسل بريدًا إلى ⁦info@airportandcitytransfer.com⁩ مع مرجع الحجز. وللتغييرات العاجلة، اتصل أيضًا على ⁦+44 208 153 0303⁩. يُحتسب إشعار الإلغاء من وقت استلام ACT له، وليس من وقت رد الموظفين."
REFUNDS = {
    "Your payment has been refunded to your original payment method.": "تم رد دفعتك إلى وسيلة الدفع الأصلية.",
    "No card payment was refunded for this booking.": "لم يتم رد أي دفعة بالبطاقة لهذا الحجز.",
}


def arabic_document_context(trip, kind, refund_message="", driver=None, download_url="", logo_uri=""):
    details = format_booking_details_for_email(trip)
    raw = getattr(trip, "booking_details", {}) or {}
    raw = raw if isinstance(raw, dict) else {}
    additional = raw.get("additional_requirements")
    additional = additional if isinstance(additional, dict) else {}
    counts = details["passenger_counts"]
    flight = details["flight_details"]
    child = details["child_infant_travel"]
    extra = details["additional_requirements"]
    car = getattr(trip, "car_type", None)
    passenger = getattr(trip, "passenger", None)
    user = getattr(passenger, "user", None)
    name = getattr(trip, "passenger_name", "") or (user.get_full_name() if user else "") or "الراكب"
    def value(v):
        return AR_VALUES.get(str(v), str(v)) if v is not None else "غير متوفر"
    def location(prefix):
        return getattr(trip, prefix + "_str", "") or f'{getattr(trip, prefix + "_lat", "")}, {getattr(trip, prefix + "_lng", "")}'
    rows = [
        ("مرجع الحجز", f"ACT-{int(trip.id):06d}"), ("اسم الراكب", name),
        ("المركبة", getattr(car, "name_ar", None) or getattr(car, "name_en", None) or "نقل خاص"),
        ("نقطة الاستلام", location("pickup")), ("الوجهة", location("dropoff")),
        ("تاريخ الرحلة", trip.trip_date.strftime("%d/%m/%Y")),
        ("وقت الاستلام", trip.trip_time.strftime("%H:%M")),
        ("قيمة الحجز", f"GBP {trip.cost:.2f}"),
        ("البالغون", counts["adults"]), ("الأطفال", counts["children"]),
        ("الرضع", counts["infants"]), ("إجمالي الركاب", counts["total"]),
        ("نوع الرحلة الجوية", value(flight["type"])),
        ("رقم الرحلة الجوية", value(flight["flight_number"])),
        ("شركة الطيران", value(flight["airline"])),
        (value(flight["time_label"]), value(flight["time"])),
        ("اسم لافتة الاستقبال", value(flight["pickup_sign_name"])),
        ("مقعد الرضيع", value(child["infant_seat_option"])),
        ("مقعد الطفل", value(child["child_seat_option"])),
        ("الاستقبال والترحيب", value(extra["meet_and_greet"])),
        ("كرسي متحرك قابل للطي", value(extra["foldable_wheelchair"])),
        # Free-form customer content is intentionally not translated.
        ("ملاحظات للسائق", extra["notes_to_driver"] if additional.get("notes_to_driver") else "لا يوجد"),
        ("الخدمات الإضافية", value(details["extra_services"])),
    ]
    if kind in ("booking", "cancellation"):
        rows += [
            ("أجرة الرحلة", f'GBP {getattr(trip, "base_trip_cost", None) or trip.cost:.2f}'),
            ("ضريبة القيمة المضافة 20%", f'GBP {(getattr(trip, "regular_vat", None) or 0) + (getattr(trip, "airport_vat", None) or 0):.2f}'),
            ("الإجمالي", f"GBP {trip.cost:.2f}"),
            ("وسيلة الدفع", "الدفع بالبطاقة"),
        ]
        if getattr(trip, "card_brand", None):
            rows.append(("البطاقة", f'{trip.card_brand} ****{getattr(trip, "last4", "") or ""}'))
    driver = driver or {}
    for key, label in (("name", "اسم السائق"), ("phone", "هاتف السائق"), ("company", "الشركة"),
                       ("vehicle", "المركبة"), ("registration", "رقم تسجيل المركبة"), ("color", "لون المركبة")):
        if driver.get(key):
            rows.append((label, value(driver[key])))
    return {
        "title": TITLES[kind], "intro": INTROS[kind], "rows": rows, "contact": CONTACT,
        "logo_uri": logo_uri,
        "website_url": "https://airportandcitytransfer.com/ar",
        "refund_message": REFUNDS.get(refund_message, "للاستفسار عن حالة الاسترداد، يرجى التواصل معنا مع ذكر مرجع الحجز." if refund_message else ""),
        "download_url": download_url, "driver_pco_url": driver.get("pco_url", ""),
    }


def render_arabic_document(trip, kind, **kwargs):
    context = arabic_document_context(trip, kind, **kwargs)
    html = render_to_string("customer/arabic_confirmation.html", context)
    # Plain text is authored from the same data; CSS/markup never leaks into email text.
    text = "\n\n".join([context["title"], context["intro"], context["refund_message"],
                        "\n".join(f"{label}: {v}" for label, v in context["rows"]),
                        context["contact"], context["website_url"]])
    for url in (context["download_url"], context["driver_pco_url"]):
        if url:
            text += "\n" + url
    return f'{context["title"]} – ACT-{int(trip.id):06d}', html, text
