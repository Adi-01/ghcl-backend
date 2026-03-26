from django.contrib import admin
from .models import JswSupplier, JswNagaurEntry

@admin.register(JswSupplier)
class JswSupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(JswNagaurEntry)
class JswNagaurEntryAdmin(admin.ModelAdmin):
    list_display = (
        'serial_number', 
        'truck_number', 
        'supplier', 
        'metric', 
        'invoice_number',  # Added here
        'entry_date', 
    )
    
    search_fields = ('serial_number', 'truck_number', 'seal_number', 'invoice_number') # Good for searching
    readonly_fields = ('entry_id', 'entry_month')
    
    fieldsets = (
        ('Core Info', {
            'fields': ('entry_id', 'serial_number', 'truck_number', 'entry_date')
        }),
        ('Cargo Details', {
            'fields': ('supplier', 'metric', 'seal_number', 'invoice_number')
        }),
        ('Additional Info', {
            'fields': ('remarks',)
        }),
        ('System Generated', {
            'fields': ('entry_month',),
            'classes': ('collapse',)
        }),
    )