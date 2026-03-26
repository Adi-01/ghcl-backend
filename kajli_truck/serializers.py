from rest_framework import serializers
from .models import KajliTruckEntry, KajliAdjustment

class KajliTruckEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = KajliTruckEntry
        fields = [
            'entry_id', 
            'godownnumber', 
            'cargo_type', 
            'bags', 
            'truck_number', 
            'loading_status', 
            'truckstatus'
        ]
        # Prevents the frontend from trying to send or modify the ID
        read_only_fields = ['entry_id']


class KajliAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KajliAdjustment
        fields = [
            'id', 
            'godownnumber', 
            'cargo_type', 
            'adjustment_value', 
            'reason', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_godownnumber(self, value):
        """
        Ensure users don't try to adjust godown 7 or numbers outside our range.
        """
        allowed = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]
        if value not in allowed:
            raise serializers.ValidationError(f"Godown {value} is not valid for adjustments.")
        return value

    def validate_adjustment_value(self, value):
        """
        Prevent zero adjustments which are unnecessary.
        """
        if value == 0:
            raise serializers.ValidationError("Adjustment value cannot be zero.")
        return value