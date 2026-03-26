from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    # The columns shown on the main list view
    list_display = (
        'user', 
        'attendance_date', 
        'worklocation', 
        'check_in_time', 
        'check_out_time', 
        'is_active_shift'
    )
    
    # Filters on the right sidebar
    list_filter = (
        'attendance_month', 
        'worklocation', 
        ('check_out_time', admin.EmptyFieldListFilter), # Easily filter for active shifts
    )
    
    # Adds a search bar at the top
    search_fields = (
        'user__email', 
        'user__username', 
        'attendance_date', 
        'worklocation'
    )
    
    # check_in_time is auto_now_add, so it must be read-only in the admin form
    readonly_fields = ('check_in_time',)
    
    # Default sorting (newest first)
    ordering = ('-check_in_time',)

    # Custom column to show a nice boolean icon for active shifts
    @admin.display(boolean=True, description='Active Shift')
    def is_active_shift(self, obj):
        return obj.check_out_time is None

    # Organizes the detail view into clean sections
    fieldsets = (
        ('User & Location', {
            'fields': ('user', 'worklocation')
        }),
        ('Time Information', {
            'fields': (
                'attendance_date', 
                'attendance_month', 
                'check_in_time', 
                'check_out_time'
            )
        }),
        ('GPS Coordinates', {
            'fields': (
                ('in_latitude', 'in_longitude'), 
                ('out_latitude', 'out_longitude')
            ),
            'classes': ('collapse',), # Hides this section behind a "Show" button
        }),
    )