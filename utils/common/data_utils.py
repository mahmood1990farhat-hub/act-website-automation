from rest_framework.exceptions import ValidationError


def validate_int_value(value , field_name="parameter", required=False):
    if value is None:
        if required:
            raise ValidationError({field_name: f"{field_name} is required."})
        return None
    if not str(value).isdigit():
        raise ValidationError({field_name: f"{field_name} must be a valid integer."})
    return int(value) 

