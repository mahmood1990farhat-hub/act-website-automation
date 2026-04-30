"""
Time conflict validation utilities for trips.

This module provides functions to check if a driver can accept a new trip
based on time conflicts with existing trips.
"""
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from ..models import Trip
import logging

logger = logging.getLogger(__name__)

# Get buffer time from settings, default to 60 minutes
TRIP_BUFFER_MINUTES = getattr(settings, 'TRIP_BUFFER_MINUTES', 60)


def driver_has_time_conflict(driver, new_trip_start_time, exclude_trip_id=None):
    """
    Check if a driver has a time conflict with an existing trip.
    
    A conflict exists if:
    - The new trip starts within the buffer time of any existing trip
    - Only checks trips with status: pending, accepted, driver_on_the_way, active
    - Ignores completed and cancelled trips
    
    Args:
        driver: BaseDriver instance
        new_trip_start_time: datetime object representing the new trip's start time
                            (should be timezone-aware)
        exclude_trip_id: Optional trip ID to exclude from conflict check (e.g., the trip being accepted)
    
    Returns:
        bool: True if there is a conflict, False otherwise
    """
    if not driver or not new_trip_start_time:
        logger.warning("driver_has_time_conflict called with None driver or trip_time")
        return False
    
    # Ensure new_trip_start_time is timezone-aware
    if timezone.is_naive(new_trip_start_time):
        new_trip_start_time = timezone.make_aware(new_trip_start_time)
    
    # Get all trips for this driver with relevant statuses
    # Only check: pending, accepted, driver_on_the_way, active
    existing_trips = Trip.objects.filter(
        base_driver=driver,
        status__in=['pending', 'accepted', 'driver_on_the_way', 'active']
    ).only(
        'id', 'trip_date', 'trip_time', 'status', 'base_driver_id'
    )
    
    # Exclude the trip being checked if provided
    if exclude_trip_id:
        existing_trips = existing_trips.exclude(id=exclude_trip_id)
    
    if not existing_trips.exists():
        logger.debug(f"No existing trips found for driver {driver.id}")
        return False
    
    # Check each existing trip for time conflict
    for existing_trip in existing_trips:
        try:
            # Combine trip_date and trip_time to get the scheduled datetime
            existing_trip_datetime = timezone.make_aware(
                datetime.combine(existing_trip.trip_date, existing_trip.trip_time)
            )
            
            # Calculate absolute time difference in minutes
            time_diff_minutes = abs((new_trip_start_time - existing_trip_datetime).total_seconds() / 60)
            
            # Check if the time difference is less than buffer time
            if time_diff_minutes < TRIP_BUFFER_MINUTES:
                logger.info(
                    f"Time conflict detected for driver {driver.id}: "
                    f"New trip at {new_trip_start_time}, existing trip {existing_trip.id} at {existing_trip_datetime}, "
                    f"difference: {time_diff_minutes:.1f} minutes (buffer: {TRIP_BUFFER_MINUTES} minutes)"
                )
                return True
                
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(
                f"Error processing trip {existing_trip.id} for conflict check: {e}",
                exc_info=True
            )
            continue
    
    return False


def get_conflicting_trip(driver, new_trip_start_time):
    """
    Get the first conflicting trip for a driver.
    
    Args:
        driver: BaseDriver instance
        new_trip_start_time: datetime object representing the new trip's start time
    
    Returns:
        Trip instance if conflict exists, None otherwise
    """
    if not driver or not new_trip_start_time:
        return None
    
    # Ensure new_trip_start_time is timezone-aware
    if timezone.is_naive(new_trip_start_time):
        new_trip_start_time = timezone.make_aware(new_trip_start_time)
    
    # Get all trips for this driver with relevant statuses
    existing_trips = Trip.objects.filter(
        base_driver=driver,
        status__in=['pending', 'accepted', 'driver_on_the_way', 'active']
    ).select_related('car_type', 'passenger__user')
    
    # Convert buffer time to timedelta
    buffer_timedelta = timedelta(minutes=TRIP_BUFFER_MINUTES)
    
    # Check each existing trip for time conflict
    for existing_trip in existing_trips:
        try:
            # Combine trip_date and trip_time to get the scheduled datetime
            existing_trip_datetime = timezone.make_aware(
                datetime.combine(existing_trip.trip_date, existing_trip.trip_time)
            )
            
            # Calculate absolute time difference
            time_diff = abs((new_trip_start_time - existing_trip_datetime).total_seconds() / 60)  # in minutes
            
            # Check if the time difference is less than buffer time
            if time_diff < TRIP_BUFFER_MINUTES:
                return existing_trip
                
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(
                f"Error processing trip {existing_trip.id} for conflict check: {e}",
                exc_info=True
            )
            continue
    
    return None

