from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """Allows access only to Staff (Django is_staff)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

