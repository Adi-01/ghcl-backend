from rest_framework import serializers
from .models import Attendance

class BaseAttendanceSerializer(serializers.ModelSerializer):
    """Base serializer to share the duration calculation logic."""
    duration = serializers.SerializerMethodField()

    def get_duration(self, obj):
        if obj.check_out_time and obj.check_in_time:
            diff = obj.check_out_time - obj.check_in_time
            hours, remainder = divmod(diff.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m"
        return "Active"

# ==========================================
# USER FACING SERIALIZERS
# ==========================================

class UserActiveShiftSerializer(serializers.ModelSerializer):
    """Lightweight serializer just for showing the active shift info."""
    class Meta:
        model = Attendance
        fields = ['attendance_id', 'worklocation', 'check_in_time'] # Changed here


class UserRecentAttendanceSerializer(BaseAttendanceSerializer):
    """Slimmed down history for the user dashboard."""
    class Meta:
        model = Attendance
        fields = [
            'attendance_id', # Changed here
            'attendance_date', 
            'check_in_time', 
            'check_out_time', 
            'worklocation', 
            'duration'
        ]

# ==========================================
# ADMIN FACING SERIALIZER
# ==========================================

class AdminAttendanceLogSerializer(BaseAttendanceSerializer):
    """Flattened data payload specifically for the Admin Data Table."""
    user_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source='user.phone_number', read_only=True) 
    
    # Explicitly redeclare these to ensure they are editable by the Admin
    check_in_time = serializers.DateTimeField(required=False)
    check_out_time = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = Attendance
        fields = [
            'attendance_id', 
            'user_name', 
            'phone_number', 
            'worklocation', 
            'check_in_time', 
            'check_out_time',
            'duration', 
            'in_latitude', 
            'in_longitude',
            'out_latitude', 
            'out_longitude'
        ]

    def get_user_name(self, obj):
        return obj.user.username if obj.user.username else obj.user.email