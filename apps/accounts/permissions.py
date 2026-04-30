from rest_framework.permissions import BasePermission 

class IsVerifiedAndProfileCompleted(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.is_profile_completed
            and user.is_admin_verified
        )


class IsPassenger(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.account_type == 'passenger' and hasattr(request.user , 'passenger_profile'))
    

class IsNormalDriver(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.account_type == 'normal_driver' and hasattr(request.user, 'base_driver'))

class IsOfficeDriver(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.account_type == 'office_driver' and hasattr(request.user, 'base_driver'))



class IsOfficeOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.account_type == 'office_owner')



