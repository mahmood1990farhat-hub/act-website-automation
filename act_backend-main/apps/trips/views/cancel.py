"""Compatibility entry point; all passenger cancellation uses the same route class.

Historically this unused handler issued an unconditional full refund. Do not
reintroduce a second refund engine. Imports are deferred during package startup.
"""
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger, IsVerifiedAndProfileCompleted


class CancelTripView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['post']

    def handle_post(self, request, trip_id):
        from apps.payments.cancellation_views import PassengerCancelTripView
        return PassengerCancelTripView().handle_post(request, trip_id)
