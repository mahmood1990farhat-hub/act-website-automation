"""Validated single-submit driver application. No legacy records modified."""
import re
from datetime import date

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers


MAX_DOC_BYTES = 10 * 1024 * 1024
APPLICATION_DOCUMENTS = (
    "pco_front", "pco_back", "dvla_front", "dvla_back", "driver_photo",
    "mot", "insurance", "v5c", "vehicle_phv", "hire_agreement", "dbs",
)


def private_document_content_type(uploaded):
    """Report document type from inspected bytes, never an uploaded filename."""
    signature = uploaded.read(16)
    uploaded.seek(0)
    if signature.startswith(b"%PDF-"):
        return "application/pdf"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise serializers.ValidationError("Unsupported driver document content")


def validate_private_driver_document(kind, uploaded):
    """Use identical private-evidence checks for initial and supplement forms."""
    if uploaded.size < 1 or uploaded.size > MAX_DOC_BYTES:
        raise serializers.ValidationError({kind: "Each document must be 10 MB or smaller."})
    first = uploaded.read(16)
    uploaded.seek(0)
    is_pdf = first.startswith(b"%PDF-")
    is_png = first.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = first.startswith(b"\xff\xd8\xff")
    if not any((is_pdf, is_png, is_jpg)):
        raise serializers.ValidationError({kind: "Upload a genuine PDF, PNG or JPEG file."})
    if kind == "driver_photo" and not (is_png or is_jpg):
        raise serializers.ValidationError({kind: "Driver photograph must be PNG or JPEG."})
    if is_png or is_jpg:
        try:
            with Image.open(uploaded) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError({kind: "Image is corrupt or invalid."})
        finally:
            uploaded.seek(0)


class UnifiedDriverApplicationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50, trim_whitespace=True)
    last_name = serializers.CharField(max_length=50, trim_whitespace=True)
    date_of_birth = serializers.DateField()
    phone_number = serializers.CharField(max_length=15)
    email = serializers.EmailField(max_length=254)
    address = serializers.CharField(max_length=255)
    postcode = serializers.CharField(max_length=20)
    pco_badge_number = serializers.CharField(max_length=50)
    pco_badge_expiry = serializers.DateField()
    years_experience = serializers.ChoiceField(
        choices=("less_than_1", "1_to_3", "3_to_5", "5_plus"),
    )
    vehicle_ownership = serializers.ChoiceField(
        choices=("phv_owner", "hiring_a_phv", "do_not_have_a_phv", "other"),
    )
    vehicle_class_code = serializers.ChoiceField(
        choices=("comfort", "comfort_xl", "executive", "executive_xl", "first"),
        required=False,
    )
    vehicle_make = serializers.CharField(max_length=80, required=False)
    vehicle_model = serializers.CharField(max_length=80, required=False)
    vehicle_year = serializers.IntegerField(required=False, min_value=2015)
    vehicle_registration = serializers.CharField(max_length=50, required=False)
    vehicle_colour = serializers.CharField(max_length=50, required=False)
    mot_expiry = serializers.DateField(required=False)
    insurance_expiry = serializers.DateField(required=False)
    accepts_pets = serializers.BooleanField(required=False)
    ownership_explanation = serializers.CharField(max_length=500, required=False)
    agrees_policies = serializers.BooleanField()
    dbs_consent = serializers.BooleanField()
    passenger_photo_disclosure_consent = serializers.BooleanField()

    pco_front = serializers.FileField()
    pco_back = serializers.FileField()
    dvla_front = serializers.FileField()
    dvla_back = serializers.FileField()
    driver_photo = serializers.ImageField()
    mot = serializers.FileField(required=False)
    insurance = serializers.FileField(required=False)
    v5c = serializers.FileField(required=False)
    vehicle_phv = serializers.FileField(required=False)
    hire_agreement = serializers.FileField(required=False)
    dbs = serializers.FileField(required=False)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_phone_number(self, value):
        normalized = re.sub(r"[\s()-]", "", value.strip())
        if not re.fullmatch(r"\+447\d{9}", normalized):
            raise serializers.ValidationError("Enter a UK mobile number in +447XXXXXXXXX format.")
        return normalized

    def validate(self, data):
        today = date.today()
        birth = data["date_of_birth"]
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 21 or age > 100:
            raise serializers.ValidationError({"date_of_birth": "Applicants must be at least 21."})
        if data["pco_badge_expiry"] <= today:
            raise serializers.ValidationError({"pco_badge_expiry": "TfL badge must not be expired."})
        if not data.get("agrees_policies") or not data.get("dbs_consent"):
            raise serializers.ValidationError({"agrees_policies": "Privacy, policies and DBS checks must be accepted."})
        if data.get("passenger_photo_disclosure_consent") is not True:
            raise serializers.ValidationError({
                "passenger_photo_disclosure_consent":
                    "The verified driver photograph must be shared with passengers as required by ACT's driver disclosure policy."
            })

        has_vehicle = data["vehicle_ownership"] != "do_not_have_a_phv"
        if has_vehicle:
            required = (
                "vehicle_class_code", "vehicle_make", "vehicle_model",
                "vehicle_year", "vehicle_registration", "vehicle_colour",
                "mot_expiry", "insurance_expiry", "accepts_pets",
                "mot", "insurance", "vehicle_phv",
            )
            missing = {field: "Required for a registered PHV vehicle." for field in required if field not in data}
            if missing:
                raise serializers.ValidationError(missing)
            for field in ("mot_expiry", "insurance_expiry"):
                if data[field] <= today:
                    raise serializers.ValidationError({field: "Must be a future date."})
            if data["vehicle_year"] > today.year:
                raise serializers.ValidationError({"vehicle_year": "Vehicle year cannot be in the future."})
            if data["vehicle_ownership"] == "phv_owner" and not data.get("v5c"):
                raise serializers.ValidationError({"v5c": "Vehicle owners must provide the V5C."})
            if data["vehicle_ownership"] == "hiring_a_phv" and not data.get("hire_agreement"):
                raise serializers.ValidationError({"hire_agreement": "Proof of lawful vehicle hire is required."})
            if data["vehicle_ownership"] == "other":
                if not data.get("ownership_explanation"):
                    raise serializers.ValidationError({"ownership_explanation": "Explain how you are authorized to use this PHV."})
                if not data.get("v5c") and not data.get("hire_agreement"):
                    raise serializers.ValidationError({"hire_agreement": "Provide proof of ownership or lawful use."})
        else:
            # A missing vehicle never becomes an approved trip-eligible one.
            vehicle_inputs = (
                "vehicle_make", "vehicle_model", "vehicle_registration",
                "vehicle_colour", "vehicle_year", "vehicle_class_code",
                "mot", "insurance", "v5c", "vehicle_phv", "hire_agreement",
            )
            if any(data.get(field) not in (None, "") for field in vehicle_inputs):
                raise serializers.ValidationError({"vehicle_ownership": "Do not submit vehicle details until you have a vehicle."})

        for kind in APPLICATION_DOCUMENTS:
            uploaded = data.get(kind)
            if uploaded:
                validate_private_driver_document(kind, uploaded)

        return data


class UnifiedVehicleSupplementSerializer(serializers.Serializer):
    """One complete vehicle and evidence submission for a pending applicant."""

    vehicle_ownership = serializers.ChoiceField(choices=("phv_owner", "hiring_a_phv", "other"))
    vehicle_class_code = serializers.ChoiceField(
        choices=("comfort", "comfort_xl", "executive", "executive_xl", "first"),
    )
    vehicle_make = serializers.CharField(max_length=80)
    vehicle_model = serializers.CharField(max_length=80)
    vehicle_year = serializers.IntegerField(min_value=2015)
    vehicle_registration = serializers.CharField(max_length=50)
    vehicle_colour = serializers.CharField(max_length=50)
    mot_expiry = serializers.DateField()
    insurance_expiry = serializers.DateField()
    accepts_pets = serializers.BooleanField()
    ownership_explanation = serializers.CharField(max_length=500, required=False)
    mot = serializers.FileField()
    insurance = serializers.FileField()
    vehicle_phv = serializers.FileField()
    v5c = serializers.FileField(required=False)
    hire_agreement = serializers.FileField(required=False)

    def validate(self, values):
        today = date.today()
        if values["vehicle_year"] > today.year:
            raise serializers.ValidationError({"vehicle_year": "Vehicle year cannot be in the future."})
        for key in ("mot_expiry", "insurance_expiry"):
            if values[key] <= today:
                raise serializers.ValidationError({key: "Expiry date must be in the future."})
        ownership = values["vehicle_ownership"]
        if ownership == "phv_owner" and not values.get("v5c"):
            raise serializers.ValidationError({"v5c": "Vehicle owners must supply their V5C."})
        if ownership == "hiring_a_phv" and not values.get("hire_agreement"):
            raise serializers.ValidationError({"hire_agreement": "Proof of lawful hire is required."})
        if ownership == "other" and (
            not values.get("ownership_explanation") or
            not (values.get("v5c") or values.get("hire_agreement"))
        ):
            raise serializers.ValidationError({
                "ownership_explanation": "Explain and document your lawful right to use the vehicle."
            })
        for key in ("mot", "insurance", "vehicle_phv", "v5c", "hire_agreement"):
            if values.get(key):
                validate_private_driver_document(key, values[key])
        return values
