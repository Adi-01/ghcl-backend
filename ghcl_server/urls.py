from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include("accounts.urls")),
    path('api/attendance/', include("attendance.urls")),
    path('api/nightchecking/', include('night_checking.urls')),
    path('api/kajli/', include('kajli_truck.urls')),
    path('api/jswnagaur/', include('jswnagaur.urls')),
]
