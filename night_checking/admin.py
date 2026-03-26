from django.contrib import admin
from .models import TruckEntry, Transporter

@admin.register(Transporter)
class TransporterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(TruckEntry)
class TruckEntryAdmin(admin.ModelAdmin):
    # Columns shown on the main list page
    list_display = (
        'entry_id', 
        'transporter_name', 
        'status', 
        'entry_date', 
        'exit_date', 
        'paper_status', 
        'tarpulin_status'
    )
    
    # Filters on the right sidebar
    list_filter = ('status', 'paper_status', 'driver_status', 'tarpulin_status')
    
    # Search bar targets
    search_fields = ('entry_id', 'transporter_name', 'remarks')
    
    # Keeps the ID read-only so admins don't accidentally break relationships
    readonly_fields = ('entry_id',)

    # Organizes the detail view into clean sections
    fieldsets = (
        ('Primary Info', {
            'fields': ('entry_id', 'transporter_name', 'status')
        }),
        ('Timestamps', {
            'fields': ('entry_date', 'exit_date')
        }),
        ('Checklist', {
            'fields': ('paper_status', 'driver_status', 'tarpulin_status')
        }),
        ('Additional Notes', {
            'fields': ('remarks',)
        }),
    )