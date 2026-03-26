from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KajliTruckEntryViewSet, KajliAdjustmentViewSet

router = DefaultRouter()
router.register(r'entries', KajliTruckEntryViewSet, basename='kajlitruck')
router.register(r'adjustments', KajliAdjustmentViewSet, basename='kajliadjustment')

urlpatterns = [
    path('', include(router.urls)),
]