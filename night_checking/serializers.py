from rest_framework import serializers
from .models import TruckEntry

class TruckEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckEntry
        fields = [
            'entry_id', 
            'truck_number',
            'transporter_name', 
            'entry_date', 
            'exit_date', 
            'paper_status', 
            'driver_status', 
            'tarpulin_status', 
            'remarks', 
            'status'
        ]
        read_only_fields = ['entry_id']