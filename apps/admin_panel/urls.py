from django.urls import path, re_path
from .views import *
from .views.instruction_files import (
    InstructionFileListView,
    InstructionFileDetailView
) 


urlpatterns = [
    # Dashboard Overview
    path('dashboard/overview/', DashboardOverviewView.as_view(), name='admin_dashboard_overview'),
    
    # Booking Control (Trips)
    path('trips/', TripListView.as_view(), name='admin_trips_list'),
    path('trips/create/', AdminCreateTripView.as_view(), name='admin_trips_create'),
    path('trips/<int:trip_id>/', TripDetailView.as_view(), name='admin_trip_detail'),
    path('trips/<int:trip_id>/update/', AdminUpdateTripView.as_view(), name='admin_trip_update'),
    path('trips/<int:trip_id>/delete/', AdminDeleteTripView.as_view(), name='admin_trip_delete'),
    path('trips/<int:trip_id>/cancel/', AdminCancelTripView.as_view(), name='admin_trip_cancel'),
    path('trips/<int:trip_id>/assign-guest-driver/', AdminAssignGuestDriverView.as_view(), name='admin_trip_assign_guest_driver'),
    path('trips/<int:trip_id>/status/', AdminUpdateTripStatusView.as_view(), name='admin_trip_status'),
    
    # Complaints Management
    path('trip-complaints/', ListTripComplaintsView.as_view(), name='admin_trip_complaints_list'),
    path('trip-complaints/<int:complaint_id>/', AdminTripComplaintDetailView.as_view(), name='admin_trip_complaint_detail'),
    path('trip-complaints/<int:complaint_id>/respond/', AdminTripComplaintRespondView.as_view(), name='admin_trip_complaint_respond'),
    path('trip-complaints/<int:complaint_id>/resolve/', AdminTripComplaintResolveView.as_view(), name='admin_trip_complaint_resolve'),
    path('trip-complaints/<int:complaint_id>/download-pdf/', AdminTripComplaintDownloadPDFView.as_view(), name='admin_trip_complaint_download_pdf'),
    path('complaints/', ListNormalComplaintsView.as_view(), name='admin_complaints_list'),
    path('resolve-complaint/<int:complaint_id>/', ResolveComplaintView.as_view(), name='admin_resolve_complaint'),
    
    # Lost Property Management
    path('lost-property/', AdminLostPropertyListView.as_view(), name='admin_lost_property_list'),
    path('lost-property/<int:lost_property_id>/', AdminLostPropertyDetailView.as_view(), name='admin_lost_property_detail'),
    path('lost-property/<int:lost_property_id>/respond/', AdminLostPropertyRespondView.as_view(), name='admin_lost_property_respond'),
    path('lost-property/<int:lost_property_id>/resolve/', AdminLostPropertyResolveView.as_view(), name='admin_lost_property_resolve'),
    path('lost-property/<int:lost_property_id>/download-pdf/', AdminLostPropertyDownloadPDFView.as_view(), name='admin_lost_property_download_pdf'),
    
    # User Management
    path('users/<int:user_id>/activate/', ActivateDeactivateUserView.as_view(), name='admin_user_activate'),
    path('users/<int:user_id>/deactivate/', ActivateDeactivateUserView.as_view(), name='admin_user_deactivate'),
    
    # User Update
    path('drivers/<int:driver_id>/update/', UpdateDriverInfoView.as_view(), name='admin_driver_update'),
    path('passengers/<int:passenger_id>/update/', UpdatePassengerInfoView.as_view(), name='admin_passenger_update'),
    
    # Driver Commission
    path('drivers/<int:driver_id>/commission/', DriverCommissionView.as_view(), name='admin_driver_commission'),
    
    # Other endpoints
    path('passengers/', PassengerUserListView.as_view(), name='admin_passengers_list'),
    path('passengers/<int:passenger_id>/', PassengerDetailView.as_view(), name='admin_passenger_detail'),
    path('normal-drivers/', NormalDriverListView.as_view(), name='admin_drivers_list'),
    path('normal-drivers/<int:driver_id>/', DriverDetailView.as_view(), name='admin_driver_detail'),
    
    # Payouts
    path('payouts/run/', AdminBulkPayoutView.as_view(), name='admin_bulk_payout'),
    
    # Withdrawal Requests
    path('withdrawal-requests/', WithdrawalRequestListView.as_view(), name='admin_withdrawal_requests_list'),
    path('withdrawal-requests/<uuid:request_id>/approve/', ApproveWithdrawalRequestView.as_view(), name='admin_withdrawal_request_approve'),
    path('withdrawal-requests/<uuid:request_id>/reject/', RejectWithdrawalRequestView.as_view(), name='admin_withdrawal_request_reject'),
    path('withdrawal-requests/<uuid:request_id>/cancel/', CancelWithdrawalRequestView.as_view(), name='admin_withdrawal_request_cancel'),
    
    # Earnings & Reporting
    path('earnings/drivers/', AdminDriverEarningsView.as_view(), name='admin_driver_earnings'),
    path('earnings/reporting/', EarningsReportingView.as_view(), name='admin_earnings_reporting'),
    path('trips/reporting/', TripsReportingView.as_view(), name='admin_trips_reporting'),
    
    # Instruction Files (Admin)
    # Support both with and without trailing slash
    re_path(r'^instruction-files/?$', InstructionFileListView.as_view(), name='admin_instruction_files_list_create'),
    re_path(r'^instruction-files/(?P<file_id>\d+)/?$', InstructionFileDetailView.as_view(), name='admin_instruction_files_detail'),

]
