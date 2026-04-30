from utils.EMDBase import EMADBaseView
from apps.trips.models import Trip, StopPoint
from ..serializers import TripWithStopPointSerializer 
from apps.trips.serializers import TripSerializer
from rest_framework.permissions import IsAdminUser
from utils.common import paginate_queryset, get_locale, remove_empty_values, notify_user
from django.db import transaction
from django.utils import timezone
from utils.utils_trip import prepare_trip_data
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from django.db.models import Count, Q, Sum
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, activate
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    create_validation_error_response,
    get_bilingual_error_message
)
from apps.passengers.models import Passenger
from apps.drivers.models import BaseDriver
from apps.vehicle.models import VehicleType
from apps.trips.services.booking_confirmation import ensure_booking_confirmation_pdf
from utils.common.notifications import NOTIFICATION_TYPE_TRIP_COMPLETED
import logging
import traceback

logger = logging.getLogger(__name__)


class TripListView(EMADBaseView):
    """
    Admin Booking Control - List and filter trips
    Supports filtering by status, date range, search, and more
    """
    http_method_names = ['get']
    permission_classes = [IsAdminUser]

    def handle_get(self, request):
        # Filter parameters
        trip_status = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')
        is_paid = request.query_params.get('is_paid')
        passenger_id = request.query_params.get('passenger_id')
        driver_id = request.query_params.get('driver_id')
        car_type_id = request.query_params.get('car_type_id')
        assigned = request.query_params.get('assigned')  # true/false or 1/0: filter by guest driver
        ordering = request.query_params.get('ordering', '-created_at')

        # Build queryset
        trips_qs = Trip.objects.select_related(
            'passenger__user',
            'base_driver__user',
            'car_type',
            'airport',
            'office'
        ).prefetch_related('stop_points').order_by(ordering)

        # Apply filters
        if trip_status:
            trips_qs = trips_qs.filter(status=trip_status)

        if date_from:
            try:
                date_from_parsed = parse_date(date_from)
                if date_from_parsed:
                    trips_qs = trips_qs.filter(trip_date__gte=date_from_parsed)
            except (ValueError, DjangoValidationError):
                pass

        if date_to:
            try:
                date_to_parsed = parse_date(date_to)
                if date_to_parsed:
                    trips_qs = trips_qs.filter(trip_date__lte=date_to_parsed)
            except (ValueError, DjangoValidationError):
                pass

        if is_paid is not None:
            is_paid_bool = is_paid.lower() == 'true'
            trips_qs = trips_qs.filter(is_paid=is_paid_bool)

        if passenger_id:
            try:
                trips_qs = trips_qs.filter(passenger_id=int(passenger_id))
            except (ValueError, TypeError):
                pass

        if driver_id:
            try:
                trips_qs = trips_qs.filter(base_driver_id=int(driver_id))
            except (ValueError, TypeError):
                pass

        if car_type_id:
            try:
                trips_qs = trips_qs.filter(car_type_id=int(car_type_id))
            except (ValueError, TypeError):
                pass

        # Guest driver filter: assigned=true (or 1) => only trips assigned to guest driver; assigned=false (or 0) => only trips not assigned to guest driver
        if assigned is not None and str(assigned).strip() != '':
            assigned_val = str(assigned).strip().lower()
            if assigned_val in ('true', '1'):
                trips_qs = trips_qs.filter(is_guest_driver=True)
            elif assigned_val in ('false', '0'):
                trips_qs = trips_qs.filter(is_guest_driver=False)

        # Search functionality
        if search:
            trips_qs = trips_qs.filter(
                Q(pickup_str__icontains=search) |
                Q(dropoff_str__icontains=search) |
                Q(passenger__user__first_name__icontains=search) |
                Q(passenger__user__last_name__icontains=search) |
                Q(passenger__user__email__icontains=search) |
                Q(passenger__user__phone_number__icontains=search) |
                Q(base_driver__user__first_name__icontains=search) |
                Q(base_driver__user__last_name__icontains=search) |
                Q(base_driver__user__email__icontains=search) |
                Q(base_driver__user__phone_number__icontains=search)
            )

        # Get statistics for all trips (before filtering)
        all_trips_stats = Trip.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            accepted=Count('id', filter=Q(status='accepted')),
            driver_on_the_way=Count('id', filter=Q(status='driver_on_the_way')),
            active=Count('id', filter=Q(status='active')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            total_revenue=Sum('cost', filter=Q(status='completed', is_paid=True)),
            unpaid_completed=Count('id', filter=Q(status='completed', is_paid=False)),
        )

        # Get filtered statistics
        filtered_stats = trips_qs.aggregate(
            total_revenue=Sum('cost', filter=Q(status='completed', is_paid=True)),
        )

        # Paginate
        page_obj, paginator = paginate_queryset(trips_qs, request)
        serializer = TripWithStopPointSerializer(page_obj, many=True, context={'request': request})

        return Response({
            "trips": serializer.data,
            "pagination": {
            "count": paginator.count,
            "num_pages": paginator.num_pages,
                "current_page": page_obj.number if hasattr(page_obj, 'number') else 1,
                "page_size": paginator.per_page,
            },
            "stats": {
                "all_time": all_trips_stats,
                "filtered": {
                    "count": paginator.count,
                    "total_revenue": float(filtered_stats['total_revenue'] or 0),
                }
            },
            "filters_applied": {
                "status": trip_status,
                "date_from": date_from,
                "date_to": date_to,
                "search": search,
                "is_paid": is_paid,
                "passenger_id": passenger_id,
                "driver_id": driver_id,
                "car_type_id": car_type_id,
                "ordering": ordering,
            }
        }, status=status.HTTP_200_OK)


class TripDetailView(EMADBaseView):
    """
    Admin Booking Control - Get detailed trip information
    """
    http_method_names = ['get']
    permission_classes = [IsAdminUser]

    def handle_get(self, request, trip_id):
        try:
            trip = Trip.objects.select_related(
                'passenger__user',
                'base_driver__user',
                'car_type',
                'airport',
                'office'
            ).prefetch_related('stop_points').get(id=trip_id)
        except Trip.DoesNotExist:
            raise NotFound("Trip not found")

        serializer = TripWithStopPointSerializer(trip, context={'request': request})

        # Additional trip details
        trip_data = serializer.data
        
        # Add related information
        if trip.passenger and trip.passenger.user:
            trip_data['passenger_details'] = {
                'id': trip.passenger.id,
                'user_id': trip.passenger.user.id,
                'full_name': f"{trip.passenger.user.first_name} {trip.passenger.user.last_name}",
                'email': trip.passenger.user.email,
                'phone_number': trip.passenger.user.phone_number,
                'is_active': trip.passenger.user.is_active,
            }
        
        if trip.base_driver and trip.base_driver.user:
            trip_data['driver_details'] = {
                'id': trip.base_driver.id,
                'user_id': trip.base_driver.user.id,
                'full_name': f"{trip.base_driver.user.first_name} {trip.base_driver.user.last_name}",
                'email': trip.base_driver.user.email,
                'phone_number': trip.base_driver.user.phone_number,
                'is_active': trip.base_driver.user.is_active,
            }
        
        if trip.car_type:
            trip_data['vehicle_type_details'] = {
                'id': trip.car_type.id,
                'name_en': trip.car_type.name_en,
                'name_ar': trip.car_type.name_ar,
                'max_passengers': trip.car_type.max_passengers_count,
            }
        
        if trip.airport:
            trip_data['airport_details'] = {
                'id': trip.airport.id,
                'name_en': trip.airport.name_en,
                'name_ar': trip.airport.name_ar,
            }

        return Response({
            "trip": trip_data
        }, status=status.HTTP_200_OK)


class AdminCreateTripView(EMADBaseView):
    """
    Admin Booking Control - Create a new trip
    POST /api/admin-panel/trips/create/
    """
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            # Prepare trip data
            raw_data = remove_empty_values(request.data)
            data = prepare_trip_data(data=raw_data, locale=locale)
            
            # Admin can specify passenger_id
            passenger_id = request.data.get('passenger_id')
            if passenger_id:
                try:
                    passenger = get_object_or_404(Passenger, id=passenger_id)
                    data['passenger'] = passenger
                except Exception:
                    message = get_bilingual_error_message(
                        'Passenger not found.',
                        'الراكب غير موجود.',
                        locale
                    )
                    return create_not_found_response(message, locale)
            else:
                message = get_bilingual_error_message(
                    'passenger_id is required.',
                    'معرف الراكب مطلوب.',
                    locale
                )
                return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Admin can optionally specify driver_id
            driver_id = request.data.get('driver_id')
            if driver_id:
                try:
                    base_driver = get_object_or_404(BaseDriver, id=driver_id)
                    data['base_driver'] = base_driver
                    # Set status to accepted if driver is assigned
                    if 'status' not in data:
                        data['status'] = 'accepted'
                except Exception:
                    message = get_bilingual_error_message(
                        'Driver not found.',
                        'السائق غير موجود.',
                        locale
                    )
                    return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Admin can set status
            if 'status' in request.data:
                data['status'] = request.data['status']
            
            # Admin can set cost manually (optional)
            if 'cost' in request.data:
                try:
                    data['cost'] = float(request.data['cost'])
                except (ValueError, TypeError):
                    pass  # Use calculated cost
            
            # Payment requirement: Admin trips should go through payment flow
            # For now, allow bypass with bypass_payment flag (should be removed in production)
            bypass_payment = request.data.get('bypass_payment', False)
            if not bypass_payment:
                message = get_bilingual_error_message(
                    'Admin trips must go through payment flow. Use /api/trips/initiate-payment/ endpoint.',
                    'يجب أن تمر رحلات المسؤول عبر تدفق الدفع. استخدم نقطة النهاية /api/trips/initiate-payment/.',
                    locale
                )
                return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # If bypassing payment, mark as paid (admin override)
            # WARNING: This should only be used for testing/manual bookings
            data['is_paid'] = True
            data['stripe_payment_intent'] = f"admin_override_{request.user.id}_{timezone.now().timestamp()}"
            
            # Create trip using serializer
            serializer = TripSerializer(data=data, context={'request': request, 'locale': locale})
            
            if serializer.is_valid():
                trip = serializer.save()
                logger.info(f"Admin {request.user.id} created trip {trip.id} for passenger {passenger_id}")
                
                message = get_bilingual_error_message(
                    'Trip created successfully.',
                    'تم إنشاء الرحلة بنجاح.',
                    locale
                )
                
                # Return trip data
                trip_serializer = TripWithStopPointSerializer(trip, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': message,
                    'data': trip_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return create_validation_error_response(
                    serializer.errors,
                    locale,
                    get_bilingual_error_message(
                        'Validation error.',
                        'خطأ في التحقق.',
                        locale
                    )
                )
                
        except ValidationError as e:
            if isinstance(e.detail, dict):
                return create_validation_error_response(e.detail, locale)
            else:
                errors = {'detail': e.detail} if not isinstance(e.detail, dict) else e.detail
                return create_validation_error_response(errors, locale)
        except Exception as e:
            logger.error(f"Error creating trip: {str(e)}")
            logger.error(traceback.format_exc())
            message = get_bilingual_error_message(
                'An error occurred while creating the trip.',
                'حدث خطأ أثناء إنشاء الرحلة.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminUpdateTripView(EMADBaseView):
    """
    Admin Booking Control - Update a trip
    PUT/PATCH /api/admin-panel/trips/<trip_id>/update/
    """
    http_method_names = ['put', 'patch']
    permission_classes = [IsAdminUser]
    
    def handle_put(self, request, trip_id):
        return self._handle_update(request, trip_id, partial=False)
    
    def handle_patch(self, request, trip_id):
        return self._handle_update(request, trip_id, partial=True)
    
    def _handle_update(self, request, trip_id, partial=False):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            trip = get_object_or_404(
                Trip.objects.select_related(
                    'passenger__user',
                    'base_driver__user',
                    'car_type',
                    'airport',
                    'office'
                ).prefetch_related('stop_points'),
                id=trip_id
            )
        except Exception:
            message = get_bilingual_error_message(
                'Trip not found.',
                'الرحلة غير موجودة.',
                locale
            )
            return create_not_found_response(message, locale)
        
        try:
            # Prepare update data
            data = request.data.copy()
            
            # Handle passenger_id update
            if 'passenger_id' in data:
                try:
                    passenger = get_object_or_404(Passenger, id=data['passenger_id'])
                    data['passenger'] = passenger.id
                except Exception:
                    message = get_bilingual_error_message(
                        'Passenger not found.',
                        'الراكب غير موجود.',
                        locale
                    )
                    return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Handle driver_id update (reassignment)
            if 'driver_id' in data:
                if data['driver_id']:
                    try:
                        base_driver = get_object_or_404(BaseDriver, id=data['driver_id'])
                        
                        # Check if driver is available (no time conflicts) if trip was cancelled by driver
                        if trip.cancelled_by_driver or trip.status == 'pending':
                            from apps.trips.utils.time_conflict import driver_has_time_conflict
                            from django.utils import timezone
                            from datetime import datetime
                            
                            # Create datetime for trip start time
                            trip_datetime = timezone.make_aware(
                                datetime.combine(trip.trip_date, trip.trip_time)
                            )
                            
                            # Check for time conflicts
                            if driver_has_time_conflict(base_driver, trip_datetime, exclude_trip_id=trip.id):
                                message = get_bilingual_error_message(
                                    'Selected driver has a time conflict with another trip. Please choose a different driver.',
                                    'السائق المحدد لديه تعارض في الوقت مع رحلة أخرى. يرجى اختيار سائق آخر.',
                                    locale
                                )
                                return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
                        
                        data['base_driver'] = base_driver.id
                        # Clear guest driver fields when assigning system driver
                        data['is_guest_driver'] = False
                        if 'guest_driver_name' not in data:
                            data['guest_driver_name'] = None
                        if 'guest_driver_phone' not in data:
                            data['guest_driver_phone'] = None
                        if 'guest_driver_company' not in data:
                            data['guest_driver_company'] = None
                        # Set status to accepted when reassigning
                        if trip.status == 'pending' or trip.cancelled_by_driver:
                            data['status'] = 'accepted'
                    except Exception:
                        message = get_bilingual_error_message(
                            'Driver not found.',
                            'السائق غير موجود.',
                            locale
                        )
                        return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
                else:
                    data['base_driver'] = None
            
            # Handle stop_points update
            if 'stop_points' in data:
                # Delete existing stop points
                trip.stop_points.all().delete()
                # New stop points will be created by serializer
            
            # Track if driver was reassigned for notifications
            driver_reassigned = False
            old_driver_id = trip.base_driver_id if trip.base_driver else None
            new_driver_id = data.get('base_driver')
            
            # Update trip
            serializer = TripSerializer(trip, data=data, partial=partial, context={'request': request, 'locale': locale})
            
            if serializer.is_valid():
                updated_trip = serializer.save()
                logger.info(f"Admin {request.user.id} updated trip {trip_id}")
                
                # Check if driver was reassigned (and it's a different driver)
                if new_driver_id and new_driver_id != old_driver_id:
                    driver_reassigned = True
                    # Send notification and email to passenger about reassignment
                    if updated_trip.passenger and updated_trip.passenger.user:
                        try:
                            from utils.common import notify_user
                            from utils.common.notifications import NOTIFICATION_TYPE_TRIP_REASSIGNED
                            from utils.common.email import send_trip_reassigned_to_passenger
                            
                            driver_user = updated_trip.base_driver.user if updated_trip.base_driver else None
                            driver_name = driver_user.get_full_name() if driver_user else "Assigned Driver"
                            
                            # Send notification
                            notify_user(
                                user=updated_trip.passenger.user_id,
                                title_en='Trip Reassigned',
                                title_ar='تم إعادة تعيين الرحلة',
                                desc_en=f'Your trip #{updated_trip.id} has been reassigned to {driver_name}.',
                                desc_ar=f'تم إعادة تعيين رحلتك #{updated_trip.id} إلى {driver_name}.',
                                locale=locale,
                                notification_type=NOTIFICATION_TYPE_TRIP_REASSIGNED,
                                trip_id=updated_trip.id
                            )
                            
                            # Send email
                            send_trip_reassigned_to_passenger(
                                updated_trip.passenger.user,
                                updated_trip,
                                is_guest_driver=False
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send reassignment notification/email for trip {updated_trip.id}: {str(e)}")
                
                message = get_bilingual_error_message(
                    'Trip updated successfully.',
                    'تم تحديث الرحلة بنجاح.',
                    locale
                )
                
                # Return updated trip data
                trip_serializer = TripWithStopPointSerializer(updated_trip, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': message,
                    'data': trip_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return create_validation_error_response(
                    serializer.errors,
                    locale,
                    get_bilingual_error_message(
                        'Validation error.',
                        'خطأ في التحقق.',
                        locale
                    )
                )
                
        except Exception as e:
            logger.error(f"Error updating trip {trip_id}: {str(e)}")
            logger.error(traceback.format_exc())
            message = get_bilingual_error_message(
                'An error occurred while updating the trip.',
                'حدث خطأ أثناء تحديث الرحلة.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminDeleteTripView(EMADBaseView):
    """
    Admin Booking Control - Delete a trip
    DELETE /api/admin-panel/trips/<trip_id>/delete/
    """
    http_method_names = ['delete']
    permission_classes = [IsAdminUser]
    
    def handle_delete(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            trip = get_object_or_404(Trip, id=trip_id)
        except Exception:
            message = get_bilingual_error_message(
                'Trip not found.',
                'الرحلة غير موجودة.',
                locale
            )
            return create_not_found_response(message, locale)
        
        try:
            # Store trip info for logging
            trip_info = {
                'id': trip.id,
                'passenger_id': trip.passenger_id,
                'status': trip.status,
                'trip_date': str(trip.trip_date),
            }
            
            # Delete trip (this will cascade delete stop_points)
            trip.delete()
            
            logger.info(f"Admin {request.user.id} deleted trip {trip_id}: {trip_info}")
            
            message = get_bilingual_error_message(
                'Trip deleted successfully.',
                'تم حذف الرحلة بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'deleted_trip_id': trip_id
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting trip {trip_id}: {str(e)}")
            logger.error(traceback.format_exc())
            message = get_bilingual_error_message(
                'An error occurred while deleting the trip.',
                'حدث خطأ أثناء حذف الرحلة.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminCancelTripView(EMADBaseView):
    """
    Admin Booking Control - Cancel a trip on behalf of the driver
    POST /api/admin-panel/trips/<trip_id>/cancel/
    
    This endpoint allows admins to cancel any trip, following the same logic as driver cancellation:
    - Trip status becomes "pending" (available for other drivers)
    - Driver is unassigned
    - Original driver cannot see or accept the trip again
    - Other drivers can see and accept the trip
    
    Request body (optional):
    {
        "cancellation_reason": "Admin cancellation reason"
    }
    """
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user
        
        try:
            trip = get_object_or_404(
                Trip.objects.select_related(
                    'passenger__user',
                    'base_driver__user'
                ),
                id=trip_id
            )
        except Exception:
            message = get_bilingual_error_message(
                'Trip not found.',
                'الرحلة غير موجودة.',
                locale
            )
            return create_not_found_response(message, locale)
        
        try:
            # Validate trip status - can only cancel if accepted, driver_on_the_way, or active
            allowed_statuses = ['accepted', 'driver_on_the_way', 'active']
            if trip.status not in allowed_statuses:
                status_choices = dict(Trip.STATUS_CHOICES)
                current_status_display = status_choices.get(trip.status, trip.status)
                message = get_bilingual_error_message(
                    f'You can only cancel trips that are accepted, on the way, or active. Current status: {current_status_display}',
                    f'يمكنك إلغاء الرحلات المقبولة أو في الطريق أو النشطة فقط. الحالة الحالية: {current_status_display}',
                    locale
                )
                return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Check if trip is already cancelled
            if trip.cancelled_by_driver:
                message = get_bilingual_error_message(
                    'This trip has already been cancelled by a driver.',
                    'تم إلغاء هذه الرحلة بالفعل من قبل سائق.',
                    locale
                )
                return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Get cancellation reason from request if provided
            cancellation_reason = request.data.get('cancellation_reason', '').strip()
            if not cancellation_reason:
                cancellation_reason = f"Cancelled by admin {user.get_full_name() or user.email}"
            
            # Use database transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                # Lock the trip row for update to prevent concurrent modifications
                # Note: select_for_update() cannot be used with select_related() on nullable foreign keys
                trip = Trip.objects.select_for_update().get(id=trip_id)
                
                # Re-validate status within transaction (may have changed)
                if trip.status not in allowed_statuses:
                    status_choices = dict(Trip.STATUS_CHOICES)
                    current_status_display = status_choices.get(trip.status, trip.status)
                    message = get_bilingual_error_message(
                        f'Trip status has changed. Current status: {current_status_display}',
                        f'تم تغيير حالة الرحلة. الحالة الحالية: {current_status_display}',
                        locale
                    )
                    return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
                
                # Get the driver who was assigned (if any) - from the locked trip
                original_driver = trip.base_driver
                
                # Use the reusable cancellation method
                # Pass the original driver to track who was cancelled
                # If no driver was assigned, we can't track a specific driver, but we still cancel
                if original_driver:
                    trip.cancel_by_driver(original_driver, cancellation_reason)
                else:
                    # If no driver was assigned, we still need to mark it as cancelled
                    # This shouldn't normally happen for accepted/active trips, but handle it gracefully
                    trip.cancelled_by_driver = True
                    trip.cancelled_by_driver_id = None  # No driver to track
                    trip.cancelled_at = timezone.now()
                    trip.cancellation_reason = cancellation_reason
                    trip.status = 'pending'
                    trip.base_driver = None
                    # Clear guest driver fields if set
                    trip.is_guest_driver = False
                    trip.guest_driver_name = None
                    trip.guest_driver_phone = None
                    trip.guest_driver_company = None
                
                trip.save(update_fields=[
                    'cancelled_by_driver',
                    'cancelled_by_driver_id',
                    'cancelled_at',
                    'cancellation_reason',
                    'base_driver',
                    'status',
                    'is_guest_driver',
                    'guest_driver_name',
                    'guest_driver_phone',
                    'guest_driver_company'
                ])
                
                # Refresh from database to verify save
                trip.refresh_from_db()
                logger.info(
                    f"Trip {trip.id} cancelled by admin {user.id} on behalf of driver. "
                    f"Status: {trip.status}, cancelled_by_driver: {trip.cancelled_by_driver}, "
                    f"cancelled_by_driver_id: {trip.cancelled_by_driver_id_id if trip.cancelled_by_driver_id else None}, "
                    f"base_driver: {trip.base_driver_id}"
                )
                
                # Fetch related objects for notifications (outside the locked query)
                passenger_user = trip.passenger.user if trip.passenger else None
                driver_user = original_driver.user if original_driver else None
                
                trip.save(update_fields=[
                    'cancelled_by_driver',
                    'cancelled_by_driver_id',
                    'cancelled_at',
                    'cancellation_reason',
                    'base_driver',
                    'status',
                    'is_guest_driver',
                    'guest_driver_name',
                    'guest_driver_phone',
                    'guest_driver_company'
                ])
                
                # Refresh from database to verify save
                trip.refresh_from_db()
                logger.info(
                    f"Trip {trip.id} cancelled by admin {user.id} on behalf of driver. "
                    f"Status: {trip.status}, cancelled_by_driver: {trip.cancelled_by_driver}, "
                    f"cancelled_by_driver_id: {trip.cancelled_by_driver_id_id if trip.cancelled_by_driver_id else None}, "
                    f"base_driver: {trip.base_driver_id}"
                )
                
                # Fetch related objects for notifications (outside the locked query)
                passenger_user = trip.passenger.user if trip.passenger else None
                driver_user = original_driver.user if original_driver else None
            
            # Send notifications and emails outside transaction to avoid long locks
            if passenger_user:
                try:
                    notify_user(
                        user=passenger_user.id,
                        title_en='Trip Cancelled by Admin',
                        title_ar='تم إلغاء الرحلة من قبل المسؤول',
                        desc_en=f'Your trip #{trip.id} has been cancelled by an administrator. We will connect you with another driver shortly.',
                        desc_ar=f'تم إلغاء رحلتك #{trip.id} من قبل مسؤول. سنقوم بالاتصال بك مع سائق آخر قريباً.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to passenger for trip {trip.id}: {str(e)}")
            
            if driver_user:
                try:
                    notify_user(
                        user=driver_user.id,
                        title_en='Trip Cancelled by Admin',
                        title_ar='تم إلغاء الرحلة من قبل المسؤول',
                        desc_en=f'Trip #{trip.id} has been cancelled by an administrator. This trip is now available for other drivers.',
                        desc_ar=f'تم إلغاء الرحلة #{trip.id} من قبل مسؤول. هذه الرحلة متاحة الآن لسائقين آخرين.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to driver for trip {trip.id}: {str(e)}")
            
            # Import email functions
            from utils.common.email import (
                send_driver_cancellation_to_passenger,
                send_driver_cancellation_to_admin
            )
            
            # Send email to passenger
            if passenger_user:
                try:
                    send_driver_cancellation_to_passenger(passenger_user, trip)
                except Exception as e:
                    logger.warning(f"Failed to send email to passenger for trip {trip.id}: {str(e)}")
            
            # Send email to admin (notification that admin cancelled)
            try:
                send_driver_cancellation_to_admin(trip)
            except Exception as e:
                logger.warning(f"Failed to send email notification for trip {trip.id}: {str(e)}")
            
            message = get_bilingual_error_message(
                'Trip cancelled successfully. The passenger and driver have been notified.',
                'تم إلغاء الرحلة بنجاح. تم إشعار الراكب والسائق.',
                locale
            )
            return Response({
                "success": True,
                "message": message,
                "data": {
                    "trip_id": trip.id,
                    "status": trip.status,
                    "cancelled_at": trip.cancelled_at.isoformat() if trip.cancelled_at else None,
                    "cancelled_by_driver_id": trip.cancelled_by_driver_id_id if trip.cancelled_by_driver_id else None
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error cancelling trip {trip_id} by admin {user.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred while cancelling the trip. Please try again.',
                'حدث خطأ أثناء إلغاء الرحلة. يرجى المحاولة مرة أخرى.',
                locale
            )
            # Pass detail with the error message for debugging
            detail = f"Data error: {str(e)}"
            return create_error_response(
                message, 
                errors=None, 
                locale=locale, 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
            )


class AdminAssignGuestDriverView(EMADBaseView):
    """
    Admin assigns a guest/external driver to a trip
    POST /api/admin-panel/trips/<trip_id>/assign-guest-driver/
    
    Request body:
    {
        "guest_driver_name": "John Doe",
        "guest_driver_phone": "+447911123456",
        "guest_driver_company": "Uber"  // Optional
    }
    """
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        
        trip = get_object_or_404(
            Trip.objects.select_related(
                'passenger__user',
                'base_driver__user',
                'car_type'
            ),
            id=trip_id
        )        
        # Validate trip status - should be pending or cancelled by driver
        if trip.status not in ['pending', 'cancelled']:
            if trip.status == 'completed':
                message = get_bilingual_error_message(
                    'Cannot assign driver to a completed trip.',
                    'لا يمكن تعيين سائق لرحلة مكتملة.',
                    locale
                )
            else:
                status_choices = dict(Trip.STATUS_CHOICES)
                current_status_display = status_choices.get(trip.status, trip.status)
                message = get_bilingual_error_message(
                    f'Can only assign guest driver to pending or cancelled trips. Current status: {current_status_display}',
                    f'يمكن تعيين سائق ضيف فقط للرحلات المعلقة أو الملغاة. الحالة الحالية: {current_status_display}',
                    locale
                )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Validate required fields
        guest_driver_name = request.data.get('guest_driver_name', '').strip()
        guest_driver_phone = request.data.get('guest_driver_phone', '').strip()
        guest_driver_company = request.data.get('guest_driver_company', '').strip()
        car_info = request.data.get('car_info', {})
        
        if not guest_driver_name:
            message = get_bilingual_error_message(
                'Guest driver name is required.',
                'اسم السائق الضيف مطلوب.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if not guest_driver_phone:
            message = get_bilingual_error_message(
                'Guest driver phone number is required.',
                'رقم هاتف السائق الضيف مطلوب.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Handle car information if provided
        guest_driver_car = None
        if car_info:
            from apps.trips.models import GuestDriverCar
            from apps.trips.serializers.guest_driver_car import GuestDriverCarSerializer
            
            # Validate car info
            car_serializer = GuestDriverCarSerializer(data=car_info)
            if not car_serializer.is_valid():
                message = get_bilingual_error_message(
                    'Invalid car information provided.',
                    'معلومات السيارة غير صالحة.',
                    locale
                )
                return create_error_response(
                    message,
                    errors=car_serializer.errors,
                    locale=locale,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Create car record
            guest_driver_car = car_serializer.save()
        
        try:
            # Update trip with guest driver information
            trip.is_guest_driver = True
            trip.guest_driver_name = guest_driver_name
            trip.guest_driver_phone = guest_driver_phone
            trip.guest_driver_company = guest_driver_company if guest_driver_company else None
            trip.guest_driver_car = guest_driver_car
            trip.base_driver = None  # Clear system driver if any
            trip.status = 'accepted'  # Set status to accepted
            trip.save(update_fields=[
                'is_guest_driver',
                'guest_driver_name',
                'guest_driver_phone',
                'guest_driver_company',
                'guest_driver_car',
                'base_driver',
                'status'
            ])

            try:
                ensure_booking_confirmation_pdf(trip)
            except Exception as e:
                logger.warning(f"Failed to generate booking confirmation PDF for trip {trip.id}: {str(e)}")
            
            logger.info(f"Admin {request.user.id} assigned guest driver to trip {trip_id}: {guest_driver_name} ({guest_driver_phone})")
            
            # Send notification to passenger
            if trip.passenger and trip.passenger.user:
                try:
                    from utils.common import notify_user
                    from utils.common.notifications import NOTIFICATION_TYPE_GUEST_DRIVER_ASSIGNED
                    from utils.common.email import send_trip_accepted_to_passenger
                    
                    # Send notification
                    notify_user(
                        user=trip.passenger.user_id,
                        title_en='External Driver Assigned',
                        title_ar='تم تعيين سائق خارجي',
                        desc_en=f'Your trip #{trip.id} has been assigned to {guest_driver_name}. Contact: {guest_driver_phone}',
                        desc_ar=f'تم تعيين رحلتك #{trip.id} إلى {guest_driver_name}. الاتصال: {guest_driver_phone}',
                        locale=locale,
                        notification_type=NOTIFICATION_TYPE_GUEST_DRIVER_ASSIGNED,
                        trip_id=trip.id
                    )
                    
                    # Send emailhtml_message = render_to_string("emails/trip_driver_details_passenger.html", context)
                    guest_driver_info = {
                        'name': guest_driver_name,
                        'phone': guest_driver_phone,
                        'company': guest_driver_company if guest_driver_company else None,
                        'car': None
                    }
                    
                    # Include car info if available
                    if guest_driver_car:
                        from apps.trips.serializers.guest_driver_car import GuestDriverCarSerializer
                        guest_driver_info['car'] = GuestDriverCarSerializer(guest_driver_car).data
                    
                    send_trip_accepted_to_passenger(
                        trip.passenger.user,
                        trip,
                        driver_user=None,
                        is_guest_driver=True,
                        guest_driver_info=guest_driver_info
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification/email for guest driver assignment to trip {trip.id}: {str(e)}")
            
            message = get_bilingual_error_message(
                'Guest driver assigned successfully. Passenger has been notified.',
                'تم تعيين السائق الضيف بنجاح. تم إشعار الراكب.',
                locale
            )
            
            # Return updated trip data
            trip_serializer = TripWithStopPointSerializer(trip, context={'request': request})
            
            return Response({
                'success': True,
                'message': message,
                'data': trip_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error assigning guest driver to trip {trip_id}: {str(e)}")
            logger.error(traceback.format_exc())
            message = get_bilingual_error_message(
                'An error occurred while assigning the guest driver.',
                'حدث خطأ أثناء تعيين السائق الضيف.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Valid trip status transitions for admin (same as driver flow)
ADMIN_TRIP_STATUS_TRANSITIONS = {
    'pending': ['accepted'],
    'accepted': ['driver_on_the_way'],
    'driver_on_the_way': ['active'],
    'active': ['completed'],
}


class AdminUpdateTripStatusView(EMADBaseView):
    """
    Admin sets trip status for full lifecycle control (e.g. for guest-driver reassignments).
    PATCH or POST /api/admin-panel/trips/<trip_id>/status/
    Body: { "status": "accepted" | "driver_on_the_way" | "active" | "completed" }
    """
    http_method_names = ['patch', 'post']
    permission_classes = [IsAdminUser]

    def _get_trip(self, trip_id):
        return get_object_or_404(
            Trip.objects.select_related('passenger__user', 'base_driver', 'car_type'),
            id=trip_id
        )

    def handle_patch(self, request, trip_id):
        return self._set_status(request, trip_id)

    def handle_post(self, request, trip_id):
        return self._set_status(request, trip_id)

    def _set_status(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        trip = self._get_trip(trip_id)
        new_status = (request.data or {}).get('status')
        if not new_status or not isinstance(new_status, str):
            message = get_bilingual_error_message(
                'Status is required. Allowed: accepted, driver_on_the_way, active, completed.',
                'الحالة مطلوبة. المسموح: accepted, driver_on_the_way, active, completed.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        new_status = new_status.strip().lower()
        allowed = ['accepted', 'driver_on_the_way', 'active', 'completed']
        if new_status not in allowed:
            message = get_bilingual_error_message(
                f'Invalid status. Allowed: {", ".join(allowed)}',
                f'حالة غير صالحة. المسموح: {", ".join(allowed)}',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        current = trip.status
        if current == new_status:
            trip_serializer = TripWithStopPointSerializer(trip, context={'request': request})
            return Response({
                'success': True,
                'message': get_bilingual_error_message('Trip already in this status.', 'الرحلة في هذه الحالة بالفعل.', locale),
                'data': trip_serializer.data
            }, status=status.HTTP_200_OK)
        allowed_next = ADMIN_TRIP_STATUS_TRANSITIONS.get(current, [])
        if new_status not in allowed_next:
            status_choices = dict(Trip.STATUS_CHOICES)
            cur_display = status_choices.get(current, current)
            message = get_bilingual_error_message(
                f'Cannot change status from {cur_display} to {new_status}. Allowed next: {", ".join(allowed_next) or "none"}.',
                f'لا يمكن تغيير الحالة من {cur_display} إلى {new_status}. المسموح التالي: {", ".join(allowed_next) or "لا شيء"}.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        if not trip.is_paid and new_status != 'accepted':
            message = get_bilingual_error_message(
                'Trip must be paid before advancing past accepted.',
                'يجب أن تكون الرحلة مدفوعة قبل التقدم بعد المقبول.',
                locale
            )
            return create_error_response(message, errors=None, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        trip.status = new_status
        trip.save(update_fields=['status'])
        logger.info(f"Admin {request.user.id} set trip {trip_id} status to {new_status} (was {current})")
        if new_status == 'completed':
            if trip.is_paid:
                try:
                    from apps.earnings.services.earnings_calculator import EarningsCalculator
                    earnings, revenue = EarningsCalculator.calculate_and_record_earnings(trip)
                    if earnings:
                        logger.info(f"Earnings recorded for trip {trip.id}: driver={earnings.net_amount}, company={revenue.amount}")
                    else:
                        logger.info(f"Earnings recorded for trip {trip.id}: company={revenue.amount} (guest driver)")
                except Exception as e:
                    logger.error(f"Error recording earnings for trip {trip.id}: {str(e)}", exc_info=True)
            try:
                notify_user(
                    user=trip.passenger.user_id,
                    title_en='Trip Completed',
                    title_ar='اكتملت الرحلة',
                    desc_en=f'Your trip #{trip.id} has been completed.',
                    desc_ar=f'اكتملت رحلتك #{trip.id}.',
                    locale=locale,
                    notification_type=NOTIFICATION_TYPE_TRIP_COMPLETED,
                    trip_id=trip.id
                )
            except Exception as e:
                logger.warning(f"Failed to send completion notification for trip {trip.id}: {str(e)}")

            try:
                from apps.trips.services.trip_tracking import stop_trip_tracking
                stop_trip_tracking(trip.id, reason="completed")
            except Exception as e:
                logger.warning(f"Failed to stop trip tracking for trip {trip.id}: {str(e)}")
        trip.refresh_from_db()
        trip_serializer = TripWithStopPointSerializer(trip, context={'request': request})
        return Response({
            'success': True,
            'message': get_bilingual_error_message('Trip status updated.', 'تم تحديث حالة الرحلة.', locale),
            'data': trip_serializer.data
        }, status=status.HTTP_200_OK)

