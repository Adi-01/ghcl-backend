from rest_framework import serializers
from .models import JswSupplier, JswNagaurEntry

class JswSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = JswSupplier
        fields = ['id', 'name']

class JswNagaurEntrySerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = JswNagaurEntry
        fields = [
            'entry_id',       # Added
            'serial_number', 
            'truck_number', 
            'invoice_number', # Added
            'metric', 
            'seal_number', 
            'supplier',       
            'supplier_name',  
            'remarks',        # Added
            'entry_date', 
            'entry_month'
        ]
        read_only_fields = ['entry_id', 'entry_month']