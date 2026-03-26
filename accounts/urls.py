from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, AdminUserViewSet

# Create DRF router
router = DefaultRouter()

# Auth routes: /auth/signup/, /auth/login/, /auth/logout/
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r'admin-users', AdminUserViewSet, basename='admin-users')



urlpatterns = [
    path("", include(router.urls)),
]
