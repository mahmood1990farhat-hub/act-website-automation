from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from apps.earnings.models import DriverEarningLedger, CompanyRevenueLedger, PayoutBatch
from apps.trips.models import Trip
from apps.drivers.models import BaseDriver
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AdminDriverEarningsView(EMADBaseView):
    """
    Admin view to see all driver earnings and what should be paid to each driver
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get query parameters
        driver_id = request.query_params.get('driver_id', None)
        status_filter = request.query_params.get('status', None)
        
        # Build query
        earnings_query = DriverEarningLedger.objects.select_related(
            'driver__user',
            'trip__passenger__user',
            'payout_batch'
        ).all()
        
        if driver_id:
            try:
                earnings_query = earnings_query.filter(driver_id=int(driver_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid driver ID',
                    'معرف السائق غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if status_filter:
            earnings_query = earnings_query.filter(status=status_filter.upper())
        
        # Aggregate by driver
        driver_earnings = earnings_query.values(
            'driver_id',
            'driver__user__first_name',
            'driver__user__last_name',
            'driver__user__email',
            'driver__user__phone_number',
            'currency'
        ).annotate(
            total_gross=Sum('gross_amount'),
            total_commission=Sum('commission_amount'),
            total_net=Sum('net_amount'),
            total_earnings=Count('id'),
            available_for_payout=Sum('net_amount', filter=Q(status='AVAILABLE')),
            pending=Sum('net_amount', filter=Q(status='PENDING')),
            locked=Sum('net_amount', filter=Q(status='LOCKED')),
            processing=Sum('net_amount', filter=Q(status='PROCESSING')),
            paid=Sum('net_amount', filter=Q(status='PAID')),
        ).order_by('-total_net')
        
        # Format response
        drivers_data = []
        for driver_data in driver_earnings:
            drivers_data.append({
                'driver_id': driver_data['driver_id'],
                'driver_name': f"{driver_data['driver__user__first_name']} {driver_data['driver__user__last_name']}".strip(),
                'driver_email': driver_data['driver__user__email'],
                'driver_phone': driver_data['driver__user__phone_number'],
                'currency': driver_data['currency'] or 'GBP',
                'total_gross': float(driver_data['total_gross'] or 0),
                'total_commission': float(driver_data['total_commission'] or 0),
                'total_net': float(driver_data['total_net'] or 0),
                'total_earnings_count': driver_data['total_earnings'],
                'available_for_payout': float(driver_data['available_for_payout'] or 0),
                'pending': float(driver_data['pending'] or 0),
                'locked': float(driver_data['locked'] or 0),
                'processing': float(driver_data['processing'] or 0),
                'paid': float(driver_data['paid'] or 0),
            })
        
        # Overall totals
        overall_totals = earnings_query.aggregate(
            total_gross=Sum('gross_amount'),
            total_commission=Sum('commission_amount'),
            total_net=Sum('net_amount'),
            total_earnings=Count('id'),
            available_for_payout=Sum('net_amount', filter=Q(status='AVAILABLE')),
            pending=Sum('net_amount', filter=Q(status='PENDING')),
            locked=Sum('net_amount', filter=Q(status='LOCKED')),
            processing=Sum('net_amount', filter=Q(status='PROCESSING')),
            paid=Sum('net_amount', filter=Q(status='PAID')),
        )
        
        return Response({
            "success": True,
            "data": {
                "drivers": drivers_data,
                "totals": {
                    "total_gross": float(overall_totals['total_gross'] or 0),
                    "total_commission": float(overall_totals['total_commission'] or 0),
                    "total_net": float(overall_totals['total_net'] or 0),
                    "total_earnings_count": overall_totals['total_earnings'],
                    "available_for_payout": float(overall_totals['available_for_payout'] or 0),
                    "pending": float(overall_totals['pending'] or 0),
                    "locked": float(overall_totals['locked'] or 0),
                    "processing": float(overall_totals['processing'] or 0),
                    "paid": float(overall_totals['paid'] or 0),
                }
            }
        }, status=status.HTTP_200_OK)


class EarningsReportingView(EMADBaseView):
    """
    Comprehensive earnings reporting API with filters, search, and pagination
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get query parameters
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        driver_id = request.query_params.get('driver_id', None)
        trip_id = request.query_params.get('trip_id', None)
        status_filter = request.query_params.get('status', None)
        search = request.query_params.get('search', None)  # Search by trip ID, driver name/email
        currency = request.query_params.get('currency', None)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Build query
        earnings_query = DriverEarningLedger.objects.select_related(
            'driver__user',
            'trip__passenger__user',
            'trip__car_type',
            'payout_batch'
        ).all()
        
        # Date filters
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                earnings_query = earnings_query.filter(created_at__gte=start_datetime)
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid start_date format. Use YYYY-MM-DD',
                    'تنسيق تاريخ البداية غير صالح. استخدم YYYY-MM-DD',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                earnings_query = earnings_query.filter(created_at__lt=end_datetime)
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid end_date format. Use YYYY-MM-DD',
                    'تنسيق تاريخ النهاية غير صالح. استخدم YYYY-MM-DD',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Driver filter
        if driver_id:
            try:
                earnings_query = earnings_query.filter(driver_id=int(driver_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid driver ID',
                    'معرف السائق غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Trip filter
        if trip_id:
            try:
                earnings_query = earnings_query.filter(trip_id=int(trip_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid trip ID',
                    'معرف الرحلة غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Status filter
        if status_filter:
            earnings_query = earnings_query.filter(status=status_filter.upper())
        
        # Currency filter
        if currency:
            earnings_query = earnings_query.filter(currency=currency.upper())
        
        # Search filter (trip ID, driver name, driver email)
        if search:
            try:
                # Try to search by trip ID
                trip_id_search = int(search)
                earnings_query = earnings_query.filter(
                    Q(trip_id=trip_id_search) |
                    Q(driver__user__first_name__icontains=search) |
                    Q(driver__user__last_name__icontains=search) |
                    Q(driver__user__email__icontains=search) |
                    Q(driver__user__phone_number__icontains=search)
                )
            except ValueError:
                # Search by name/email/phone only
                earnings_query = earnings_query.filter(
                    Q(driver__user__first_name__icontains=search) |
                    Q(driver__user__last_name__icontains=search) |
                    Q(driver__user__email__icontains=search) |
                    Q(driver__user__phone_number__icontains=search)
                )
        
        # Get total count before pagination
        total_count = earnings_query.count()
        
        # Apply pagination
        earnings = earnings_query.order_by('-created_at')[offset:offset + page_size]
        
        # Serialize earnings
        earnings_data = []
        for earning in earnings:
            earnings_data.append({
                'id': earning.id,
                'driver': {
                    'id': earning.driver.id,
                    'name': f"{earning.driver.user.first_name} {earning.driver.user.last_name}".strip(),
                    'email': earning.driver.user.email,
                    'phone': earning.driver.user.phone_number,
                },
                'trip': {
                    'id': earning.trip.id,
                    'cost': float(earning.trip.cost),
                    'status': earning.trip.status,
                    'trip_date': earning.trip.trip_date.isoformat() if earning.trip.trip_date else None,
                    'car_type': earning.trip.car_type.name_en if earning.trip.car_type else None,
                },
                'gross_amount': float(earning.gross_amount),
                'commission_amount': float(earning.commission_amount),
                'net_amount': float(earning.net_amount),
                'currency': earning.currency,
                'status': earning.status,
                'stripe_transfer_id': earning.stripe_transfer_id,
                'payout_batch_id': earning.payout_batch.batch_id if earning.payout_batch else None,
                'created_at': earning.created_at.isoformat(),
                'paid_at': earning.paid_at.isoformat() if earning.paid_at else None,
            })
        
        # Calculate summary statistics
        summary = earnings_query.aggregate(
            total_gross=Sum('gross_amount'),
            total_commission=Sum('commission_amount'),
            total_net=Sum('net_amount'),
            total_count=Count('id'),
            available=Sum('net_amount', filter=Q(status='AVAILABLE')),
            pending=Sum('net_amount', filter=Q(status='PENDING')),
            locked=Sum('net_amount', filter=Q(status='LOCKED')),
            processing=Sum('net_amount', filter=Q(status='PROCESSING')),
            paid=Sum('net_amount', filter=Q(status='PAID')),
        )
        
        return Response({
            "success": True,
            "data": {
                "earnings": earnings_data,
                "summary": {
                    "total_gross": float(summary['total_gross'] or 0),
                    "total_commission": float(summary['total_commission'] or 0),
                    "total_net": float(summary['total_net'] or 0),
                    "total_count": summary['total_count'],
                    "available": float(summary['available'] or 0),
                    "pending": float(summary['pending'] or 0),
                    "locked": float(summary['locked'] or 0),
                    "processing": float(summary['processing'] or 0),
                    "paid": float(summary['paid'] or 0),
                },
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                    "has_next": offset + page_size < total_count,
                    "has_previous": page > 1,
                }
            }
        }, status=status.HTTP_200_OK)


class TripsReportingView(EMADBaseView):
    """
    Comprehensive trips reporting API with filters, search, and pagination
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get query parameters
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        trip_id = request.query_params.get('trip_id', None)
        driver_id = request.query_params.get('driver_id', None)
        passenger_id = request.query_params.get('passenger_id', None)
        status_filter = request.query_params.get('status', None)
        is_paid = request.query_params.get('is_paid', None)
        car_type_id = request.query_params.get('car_type_id', None)
        search = request.query_params.get('search', None)  # Search by trip ID, passenger name/email, driver name/email
        min_cost = request.query_params.get('min_cost', None)
        max_cost = request.query_params.get('max_cost', None)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Build query
        trips_query = Trip.objects.select_related(
            'passenger__user',
            'base_driver__user',
            'car_type',
            'airport'
        ).prefetch_related('stoppoint_set').all()
        
        # Date filters (using trip_date or created_at)
        date_field = request.query_params.get('date_field', 'trip_date')  # 'trip_date' or 'created_at'
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                if date_field == 'trip_date':
                    trips_query = trips_query.filter(trip_date__gte=start_datetime.date())
                else:
                    trips_query = trips_query.filter(created_at__gte=start_datetime)
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid start_date format. Use YYYY-MM-DD',
                    'تنسيق تاريخ البداية غير صالح. استخدم YYYY-MM-DD',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                if date_field == 'trip_date':
                    trips_query = trips_query.filter(trip_date__lte=end_datetime.date())
                else:
                    end_datetime = end_datetime + timedelta(days=1)
                    trips_query = trips_query.filter(created_at__lt=end_datetime)
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid end_date format. Use YYYY-MM-DD',
                    'تنسيق تاريخ النهاية غير صالح. استخدم YYYY-MM-DD',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Trip ID filter
        if trip_id:
            try:
                trips_query = trips_query.filter(id=int(trip_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid trip ID',
                    'معرف الرحلة غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Driver filter
        if driver_id:
            try:
                trips_query = trips_query.filter(base_driver_id=int(driver_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid driver ID',
                    'معرف السائق غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Passenger filter
        if passenger_id:
            try:
                trips_query = trips_query.filter(passenger_id=int(passenger_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid passenger ID',
                    'معرف الراكب غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Status filter
        if status_filter:
            trips_query = trips_query.filter(status=status_filter.lower())
        
        # Payment filter
        if is_paid is not None:
            trips_query = trips_query.filter(is_paid=is_paid.lower() == 'true')
        
        # Car type filter
        if car_type_id:
            try:
                trips_query = trips_query.filter(car_type_id=int(car_type_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid car type ID',
                    'معرف نوع السيارة غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Cost filters
        if min_cost:
            try:
                trips_query = trips_query.filter(cost__gte=Decimal(min_cost))
            except (ValueError, TypeError):
                message = get_bilingual_error_message(
                    'Invalid min_cost',
                    'الحد الأدنى للتكلفة غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if max_cost:
            try:
                trips_query = trips_query.filter(cost__lte=Decimal(max_cost))
            except (ValueError, TypeError):
                message = get_bilingual_error_message(
                    'Invalid max_cost',
                    'الحد الأقصى للتكلفة غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Search filter
        if search:
            try:
                # Try to search by trip ID
                trip_id_search = int(search)
                trips_query = trips_query.filter(
                    Q(id=trip_id_search) |
                    Q(passenger__user__first_name__icontains=search) |
                    Q(passenger__user__last_name__icontains=search) |
                    Q(passenger__user__email__icontains=search) |
                    Q(passenger__user__phone_number__icontains=search) |
                    Q(base_driver__user__first_name__icontains=search) |
                    Q(base_driver__user__last_name__icontains=search) |
                    Q(base_driver__user__email__icontains=search) |
                    Q(base_driver__user__phone_number__icontains=search)
                )
            except ValueError:
                # Search by name/email/phone only
                trips_query = trips_query.filter(
                    Q(passenger__user__first_name__icontains=search) |
                    Q(passenger__user__last_name__icontains=search) |
                    Q(passenger__user__email__icontains=search) |
                    Q(passenger__user__phone_number__icontains=search) |
                    Q(base_driver__user__first_name__icontains=search) |
                    Q(base_driver__user__last_name__icontains=search) |
                    Q(base_driver__user__email__icontains=search) |
                    Q(base_driver__user__phone_number__icontains=search)
                )
        
        # Get total count before pagination
        total_count = trips_query.count()
        
        # Apply pagination
        trips = trips_query.order_by('-created_at')[offset:offset + page_size]
        
        # Serialize trips
        trips_data = []
        for trip in trips:
            trips_data.append({
                'id': trip.id,
                'passenger': {
                    'id': trip.passenger.id,
                    'name': f"{trip.passenger.user.first_name} {trip.passenger.user.last_name}".strip(),
                    'email': trip.passenger.user.email,
                    'phone': trip.passenger.user.phone_number,
                },
                'driver': {
                    'id': trip.base_driver.id,
                    'name': f"{trip.base_driver.user.first_name} {trip.base_driver.user.last_name}".strip(),
                    'email': trip.base_driver.user.email,
                    'phone': trip.base_driver.user.phone_number,
                } if trip.base_driver else None,
                'trip_date': trip.trip_date.isoformat() if trip.trip_date else None,
                'trip_time': str(trip.trip_time) if trip.trip_time else None,
                'pickup_location': {
                    'lat': float(trip.pickup_lat) if trip.pickup_lat else None,
                    'lng': float(trip.pickup_lng) if trip.pickup_lng else None,
                    'address': trip.pickup_str,
                },
                'dropoff_location': {
                    'lat': float(trip.dropoff_lat) if trip.dropoff_lat else None,
                    'lng': float(trip.dropoff_lng) if trip.dropoff_lng else None,
                    'address': trip.dropoff_str,
                },
                'car_type': {
                    'id': trip.car_type.id,
                    'name': trip.car_type.name_en,
                } if trip.car_type else None,
                'cost': float(trip.cost) if trip.cost else 0,
                'base_trip_cost': float(trip.base_trip_cost) if trip.base_trip_cost else None,
                'regular_vat': float(trip.regular_vat) if trip.regular_vat else None,
                'airport_vat': float(trip.airport_vat) if trip.airport_vat else None,
                'min_adjustment': float(trip.min_adjustment) if trip.min_adjustment else None,
                'status': trip.status,
                'is_paid': trip.is_paid,
                'stripe_payment_intent': trip.stripe_payment_intent,
                'distance_miles': float(trip.distance_miles) if trip.distance_miles else None,
                'expected_trip_duration_minutes': trip.expected_trip_duration_minutes,
                'airport': {
                    'id': trip.airport.id,
                    'name': trip.airport.name_en,
                } if trip.airport else None,
                'airport_direction': trip.airport_direction,
                'passengers_count': trip.passengers_count,
                'large_suitcase': trip.large_suitcase,
                'small_suitcase': trip.small_suitcase,
                'created_at': trip.created_at.isoformat(),
                'has_earning': hasattr(trip, 'driver_earning'),
                'has_company_revenue': hasattr(trip, 'company_revenue'),
            })
        
        # Calculate summary statistics
        summary = trips_query.aggregate(
            total_trips=Count('id'),
            total_revenue=Sum('cost', filter=Q(is_paid=True)),
            total_unpaid=Sum('cost', filter=Q(is_paid=False)),
            completed_trips=Count('id', filter=Q(status='completed')),
            cancelled_trips=Count('id', filter=Q(status='cancelled')),
            pending_trips=Count('id', filter=Q(status='pending')),
            active_trips=Count('id', filter=Q(status='active')),
        )
        
        return Response({
            "success": True,
            "data": {
                "trips": trips_data,
                "summary": {
                    "total_trips": summary['total_trips'],
                    "total_revenue": float(summary['total_revenue'] or 0),
                    "total_unpaid": float(summary['total_unpaid'] or 0),
                    "completed_trips": summary['completed_trips'],
                    "cancelled_trips": summary['cancelled_trips'],
                    "pending_trips": summary['pending_trips'],
                    "active_trips": summary['active_trips'],
                },
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                    "has_next": offset + page_size < total_count,
                    "has_previous": page > 1,
                }
            }
        }, status=status.HTTP_200_OK)

