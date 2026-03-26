import string
from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string

# 1. Create a callable function to generate the ID
def generate_attendance_id():
    """Generates a secure, random 16-character alphanumeric string."""
    allowed_chars = string.ascii_letters + string.digits
    return get_random_string(length=16, allowed_chars=allowed_chars)

class Attendance(models.Model):
    # 2. Add the custom ID field and set it as the Primary Key
    attendance_id = models.CharField(
        max_length=16,
        primary_key=True,       # Replaces the default auto-incrementing 'id'
        default=generate_attendance_id, 
        editable=False,         # Prevents it from being changed in the admin panel
        unique=True,
        db_index=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='attendances'
    )
    
    # Accepts whatever string the frontend sends
    worklocation = models.CharField(max_length=255)
    
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    
    # Storing dates as strings in the specific formats you requested
    attendance_date = models.CharField(max_length=20, db_index=True)   # e.g., "16-mar-2026"
    attendance_month = models.CharField(max_length=20, db_index=True)  # e.g., "mar-2026"
    
    # Coordinates (DecimalField is best practice for lat/long)
    in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ['-check_in_time']
        verbose_name_plural = "Attendances"

    def __str__(self):
        return f"{self.user.email} | {self.attendance_date}"