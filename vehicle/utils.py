"""
Utility functions for vehicle-related operations
"""
from .models import VehicleType
import logging

logger = logging.getLogger(__name__)

# Mapping from onboarding request vehicle_type string to VehicleType name_en
VEHICLE_TYPE_MAPPING = {
    '5_seater_standard': 'Standard PHV',
    '7_seaters': '7 Seaters PHV',
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
    
    # Get the VehicleType name from mapping
    vehicle_type_name = VEHICLE_TYPE_MAPPING.get(vehicle_type_string)
    
    if not vehicle_type_name:
        logger.warning(f"Unknown vehicle_type string: {vehicle_type_string}")
        return None
    
    try:
        # Try to find VehicleType by name_en
        vehicle_type = VehicleType.objects.filter(name_en__iexact=vehicle_type_name).first()
        
        if not vehicle_type:
            logger.warning(f"VehicleType with name_en='{vehicle_type_name}' not found in database")
            # Try alternative names
            if vehicle_type_string == '5_seater_standard':
                # Try variations
                vehicle_type = VehicleType.objects.filter(
                    name_en__icontains='Standard'
                ).first()
            elif vehicle_type_string == '7_seaters':
                vehicle_type = VehicleType.objects.filter(
                    name_en__icontains='7'
                ).first()
        
        return vehicle_type
    except Exception as e:
        logger.error(f"Error getting VehicleType for '{vehicle_type_string}': {e}")
        return None

