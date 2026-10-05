"""
Utility functions for vehicle-related operations
"""
from .models import VehicleType
import logging

logger = logging.getLogger(__name__)

# Stable mappings for onboarding categories that correspond exactly to ACT classes.
VEHICLE_TYPE_CODE_MAPPING = {
    '5_seater_standard': 'comfort',
    '7_seaters': 'comfort_xl',
}

# Legacy/general onboarding categories do not yet map one-to-one to a premium ACT class.
VEHICLE_TYPE_NAME_FALLBACK = {
    'van_transporter': 'Van/Transporter',
    'other': 'Other',
}

def get_vehicle_type_from_string(vehicle_type_string):
    """
    Map onboarding request vehicle_type string to VehicleType instance.
    
    Args:
        vehicle_type_string: String from DriverOnboardingRequest.vehicle_type
                            (e.g., '5_seater_standard', '7_seaters')
    
    Returns:
        VehicleType instance or None if not found
    """
    if not vehicle_type_string:
        return None
    
    vehicle_type_code = VEHICLE_TYPE_CODE_MAPPING.get(vehicle_type_string)
    fallback_name = VEHICLE_TYPE_NAME_FALLBACK.get(vehicle_type_string)

    if not vehicle_type_code and not fallback_name:
        logger.warning(f"Unknown vehicle_type string: {vehicle_type_string}")
        return None

    try:
        if vehicle_type_code:
            vehicle_type = VehicleType.objects.filter(code=vehicle_type_code).first()
            if not vehicle_type:
                logger.warning(
                    f"VehicleType with code='{vehicle_type_code}' not found in database"
                )
            return vehicle_type

        # Preserve general categories until ACT defines an exact class mapping.
        vehicle_type = VehicleType.objects.filter(name_en__iexact=fallback_name).first()
        if not vehicle_type:
            logger.warning(f"VehicleType with name_en='{fallback_name}' not found in database")
        return vehicle_type
    except Exception as e:
        logger.error(f"Error getting VehicleType for '{vehicle_type_string}': {e}")
        return None

