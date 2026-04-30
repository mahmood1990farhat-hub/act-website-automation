from utils.EMDBase import EMADBaseView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from apps.trips.models import Trip
from apps.drivers.models.onboarding import DriverOnboardingRequest
from apps.drivers.models import NormalDriver
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class DashboardOverviewView(EMADBaseView):
    """
    Admin Dashboard Overview API
    Provides quick stats and overview data for the admin dashboard
    """
    http_method_names = ['get']
    permission_classes = [IsAdminUser]

    def handle_get(self, request):
        """Get dashboard overview statistics"""
        
        # Date ranges for filtering
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        
        # === TRIPS STATISTICS ===
        trips_stats = Trip.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            accepted=Count('id', filter=Q(status='accepted')),
            driver_on_the_way=Count('id', filter=Q(status='driver_on_the_way')),
            active=Count('id', filter=Q(status='active')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
        )
        
        # Trips by period
        trips_today = Trip.objects.filter(created_at__date=today).count()
        trips_this_week = Trip.objects.filter(created_at__date__gte=this_week_start).count()
        trips_this_month = Trip.objects.filter(created_at__date__gte=this_month_start).count()
        trips_last_month = Trip.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # === REVENUE STATISTICS ===
        revenue_stats = Trip.objects.filter(
            status='completed',
            is_paid=True
        ).aggregate(
            total_revenue=Sum('cost'),
            total_trips=Count('id')
        )
        
        revenue_today = Trip.objects.filter(
            status='completed',
            is_paid=True,
            created_at__date=today
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        revenue_this_week = Trip.objects.filter(
            status='completed',
            is_paid=True,
            created_at__date__gte=this_week_start
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        revenue_this_month = Trip.objects.filter(
            status='completed',
            is_paid=True,
            created_at__date__gte=this_month_start
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        revenue_last_month = Trip.objects.filter(
            status='completed',
            is_paid=True,
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        # Unpaid completed trips
        unpaid_completed = Trip.objects.filter(
            status='completed',
            is_paid=False
        ).aggregate(
            total_amount=Sum('cost'),
            count=Count('id')
        )
        
        # === DRIVERS STATISTICS ===
        drivers_stats = CustomUser.objects.filter(account_type='normal_driver').aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
            verified=Count('id', filter=Q(is_admin_verified=True)),
            unverified=Count('id', filter=Q(is_admin_verified=False)),
        )
        
        # Drivers with completed profile
        drivers_with_profile = CustomUser.objects.filter(
            account_type='normal_driver',
            is_profile_completed=True
        ).count()
        
        # === PASSENGERS STATISTICS ===
        passengers_stats = CustomUser.objects.filter(account_type='passenger').aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
        )
        
        # === ONBOARDING REQUESTS STATISTICS ===
        onboarding_stats = DriverOnboardingRequest.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            step1_approved=Count('id', filter=Q(status='step1_approved')),
            step1_rejected=Count('id', filter=Q(status='step1_rejected')),
            documents_uploaded=Count('id', filter=Q(status='documents_uploaded')),
            final_approved=Count('id', filter=Q(status='final_approved')),
            final_rejected=Count('id', filter=Q(status='final_rejected')),
            needs_modification=Count('id', filter=Q(status='needs_modification')),
        )
        
        # === RECENT ACTIVITY ===
        recent_trips = Trip.objects.select_related(
            'passenger__user',
            'base_driver__user'
        ).order_by('-created_at')[:10]
        
        recent_activity = []
        for trip in recent_trips:
            recent_activity.append({
                'id': trip.id,
                'type': 'trip',
                'status': trip.status,
                'passenger_name': f"{trip.passenger.user.first_name} {trip.passenger.user.last_name}" if trip.passenger and trip.passenger.user else "N/A",
                'driver_name': f"{trip.base_driver.user.first_name} {trip.base_driver.user.last_name}" if trip.base_driver and trip.base_driver.user else "N/A",
                'cost': str(trip.cost),
                'created_at': trip.created_at.isoformat(),
            })
        
        # Recent onboarding requests
        recent_onboarding = DriverOnboardingRequest.objects.select_related('user').order_by('-id')[:5]
        onboarding_activity = []
        for req in recent_onboarding:
            onboarding_activity.append({
                'id': req.id,
                'type': 'onboarding',
                'status': req.status,
                'full_name': req.full_name,
                'email': req.email_address,
                'created_at': req.user.date_joined.isoformat() if req.user else None,
            })
        
        # === PERFORMANCE METRICS ===
        # Average trip value
        avg_trip_value = 0
        if revenue_stats['total_trips'] and revenue_stats['total_trips'] > 0:
            avg_trip_value = float(revenue_stats['total_revenue'] or 0) / revenue_stats['total_trips']
        
        # Cancellation rate
        cancellation_rate = 0
        if trips_stats['total'] and trips_stats['total'] > 0:
            cancellation_rate = (trips_stats['cancelled'] / trips_stats['total']) * 100
        
        # Completion rate
        completion_rate = 0
        if trips_stats['total'] and trips_stats['total'] > 0:
            completion_rate = (trips_stats['completed'] / trips_stats['total']) * 100
        
        # Response data
        response_data = {
            'trips': {
                'total': trips_stats['total'],
                'by_status': {
                    'pending': trips_stats['pending'],
                    'accepted': trips_stats['accepted'],
                    'driver_on_the_way': trips_stats['driver_on_the_way'],
                    'active': trips_stats['active'],
                    'completed': trips_stats['completed'],
                    'cancelled': trips_stats['cancelled'],
                },
                'by_period': {
                    'today': trips_today,
                    'this_week': trips_this_week,
                    'this_month': trips_this_month,
                    'last_month': trips_last_month,
                }
            },
            'revenue': {
                'total': float(revenue_stats['total_revenue'] or 0),
                'total_trips': revenue_stats['total_trips'],
                'average_trip_value': round(avg_trip_value, 2),
                'by_period': {
                    'today': float(revenue_today),
                    'this_week': float(revenue_this_week),
                    'this_month': float(revenue_this_month),
                    'last_month': float(revenue_last_month),
                },
                'unpaid': {
                    'amount': float(unpaid_completed['total_amount'] or 0),
                    'trips_count': unpaid_completed['count'],
                }
            },
            'drivers': {
                'total': drivers_stats['total'],
                'active': drivers_stats['active'],
                'inactive': drivers_stats['inactive'],
                'verified': drivers_stats['verified'],
                'unverified': drivers_stats['unverified'],
                'with_completed_profile': drivers_with_profile,
            },
            'passengers': {
                'total': passengers_stats['total'],
                'active': passengers_stats['active'],
                'inactive': passengers_stats['inactive'],
            },
            'onboarding': {
                'total': onboarding_stats['total'],
                'pending': onboarding_stats['pending'],
                'step1_approved': onboarding_stats['step1_approved'],
                'step1_rejected': onboarding_stats['step1_rejected'],
                'documents_uploaded': onboarding_stats['documents_uploaded'],
                'final_approved': onboarding_stats['final_approved'],
                'final_rejected': onboarding_stats['final_rejected'],
                'needs_modification': onboarding_stats['needs_modification'],
            },
            'performance': {
                'average_trip_value': round(avg_trip_value, 2),
                'cancellation_rate': round(cancellation_rate, 2),
                'completion_rate': round(completion_rate, 2),
            },
            'recent_activity': {
                'trips': recent_activity,
                'onboarding': onboarding_activity,
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

