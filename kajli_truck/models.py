import string
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone

def generate_entry_id():
    """Generates a secure, random 16-character alphanumeric string."""
    allowed_chars = string.ascii_letters + string.digits
    return get_random_string(length=16, allowed_chars=allowed_chars)

class KajliTruckEntry(models.Model):
    CARGO_CHOICES = [
        ('RBC', 'RBC'),
        ('LSA', 'LSA'),
        ('DSA', 'DSA'),
    ]

    LOADING_CHOICES = [
        ('IN', 'IN'),
        ('OUT', 'OUT'),
    ]

    TRUCK_STATUS_CHOICES = [
        ('IN - complete', 'IN - complete'),
        ('IN - pending', 'IN - pending'),
        ('OUT - complete', 'OUT - complete'),
        ('OUT - pending', 'OUT - pending'),
    ]

    # Primary Key
    entry_id = models.CharField(
        max_length=16,
        primary_key=True,
        default=generate_entry_id,
        editable=False,
        unique=True,
        db_index=True
    )

    # Core Data
    godownnumber = models.IntegerField(db_index=True)
    cargo_type = models.CharField(max_length=3, choices=CARGO_CHOICES, db_index=True)
    bags = models.IntegerField()
    truck_number = models.CharField(max_length=50)
    
    # Statuses
    loading_status = models.CharField(max_length=3, choices=LOADING_CHOICES)
    truckstatus = models.CharField(max_length=20, choices=TRUCK_STATUS_CHOICES)

    entry_date = models.DateTimeField(default=timezone.now)
    entry_month = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "Kajli Truck Entries"

    def __str__(self):
        return f"{self.truck_number} - {self.truckstatus}"
    
    def save(self, *args, **kwargs):
        if self.entry_date:
            self.entry_month = self.entry_date.strftime('%b-%Y').lower() 
            
        super().save(*args, **kwargs)
    

class KajliAdjustment(models.Model):
    godownnumber = models.IntegerField()
    cargo_type = models.CharField(max_length=3, choices=[('RBC', 'RBC'), ('LSA', 'LSA'), ('DSA', 'DSA')])
    adjustment_value = models.IntegerField() # Can be positive or negative
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GD{self.godownnumber} - {self.cargo_type}: {self.adjustment_value}"