from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JswSupplierViewSet, JswNagaurEntryViewSet

router = DefaultRouter()
router.register(r'suppliers', JswSupplierViewSet, basename='jswsupplier')
router.register(r'entries', JswNagaurEntryViewSet, basename='jswentry')

urlpatterns = [
    path('', include(router.urls)),
]