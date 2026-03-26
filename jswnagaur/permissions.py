from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """Allows access only to Staff (Django is_staff)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

class IsJswUser(permissions.BasePermission):
    """Allows access to JSW Nagaur users."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        labels = request.user.labels or []
        if isinstance(labels, list):
            lower_labels = [str(label).lower().strip() for label in labels]
            # They must be logged in AND have the 'jsw' label (Admins bypass via the | operator in the ViewSet)
            return "jsw" in lower_labels
            
        return False