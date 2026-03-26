from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceViewSet, AdminAttendanceLogViewSet

router = DefaultRouter()
router.register(r'', AttendanceViewSet, basename='attendance')
router.register(r'admin-logs', AdminAttendanceLogViewSet, basename='admin-logs')

urlpatterns = [
    path('', include(router.urls)),
]