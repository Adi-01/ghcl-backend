from django.contrib import admin
from .models import KajliTruckEntry, KajliAdjustment

@admin.register(KajliTruckEntry)
class KajliTruckEntryAdmin(admin.ModelAdmin):
    # What columns show up in the main list view
    list_display = (
        'entry_id', 
        'truck_number', 
        'cargo_type', 
        'godownnumber', 
        'bags', 
        'loading_status', 
        'truckstatus'
    )
    
    # Creates a sidebar to quickly filter down records
    list_filter = (
        'cargo_type', 
        'loading_status', 
        'truckstatus', 
        'godownnumber'
    )
    
    # Allows you to search by ID or Truck Number via the search bar
    search_fields = ('entry_id', 'truck_number')
    
    # Protects the secure ID from being tampered with in the admin panel
    readonly_fields = ('entry_id',)

    # Groups the fields neatly when you click into a specific record to edit it
    fieldsets = (
        ('Primary Info', {
            'fields': ('entry_id', 'truck_number')
        }),
        ('Cargo Details', {
            'fields': ('godownnumber', 'cargo_type', 'bags')
        }),
        ('Status Tracking', {
            'fields': ('loading_status', 'truckstatus')
        }),
    ) 


@admin.register(KajliAdjustment)
class KajliAdjustmentAdmin(admin.ModelAdmin):
    # What to show in the list view
    list_display = (
        'id', 
        'godownnumber', 
        'cargo_type', 
        'adjustment_value', 
        'reason', 
        'created_at'
    )
    
    # Filtering options for the sidebar
    list_filter = (
        'cargo_type', 
        'godownnumber', 
        'created_at'
    )
    
    # Search for specific reasons or godowns
    search_fields = ('reason', 'godownnumber')
    
    # Sort by the most recent adjustment first
    ordering = ('-created_at',)