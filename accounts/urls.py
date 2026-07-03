from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, AdminUserViewSet, server_health_check, UserProfileView

# Create DRF router
router = DefaultRouter()

# Auth routes: /auth/signup/, /auth/login/, /auth/logout/
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r'admin-users', AdminUserViewSet, basename='admin-users')



urlpatterns = [
    path("", include(router.urls)),
    path('health/', server_health_check),
    path('user/me/', UserProfileView.as_view(), name='user-profile'),
]
