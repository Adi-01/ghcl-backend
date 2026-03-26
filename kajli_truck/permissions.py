from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """Allows access only to Staff (Django is_staff)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

class IsModerator(permissions.BasePermission):
    """Allows access if the user has 'moderator' in their JSON labels list."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        labels = request.user.labels or []
        if isinstance(labels, list):
            # Safely lowercase all items in the list
            lower_labels = [str(label).lower().strip() for label in labels]
            return "moderator" in lower_labels
            
        return False