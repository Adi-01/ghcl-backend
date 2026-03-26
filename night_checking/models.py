import string
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

def generate_entry_id():
    allowed_chars = string.ascii_letters + string.digits
    return get_random_string(length=16, allowed_chars=allowed_chars)

# 1. 🔥 NEW: The Permanent Master List
class Transporter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['name'] # Always sort alphabetically

    def __str__(self):
        return self.name

# 2. Update your existing TruckEntry model
class TruckEntry(models.Model):
    STATUS_CHOICES = [
        ('IN', 'IN'),
        ('OUT', 'OUT'),
    ]

    entry_id = models.CharField(max_length=16, primary_key=True, default=generate_entry_id, editable=False, unique=True, db_index=True)
    truck_number = models.CharField(max_length=50) 
    transporter_name = models.CharField(max_length=255)
    
    entry_date = models.DateTimeField(default=timezone.now) 
    exit_date = models.DateTimeField(null=True, blank=True)
    entry_month = models.CharField(max_length=20, blank=True)
    
    paper_status = models.BooleanField(default=False, verbose_name="Paper Status OK?")
    driver_status = models.BooleanField(default=False, verbose_name="Driver Status OK?")
    tarpulin_status = models.BooleanField(default=False, verbose_name="Tarpulin Status OK?")
    
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='IN', db_index=True)

    class Meta:
        ordering = ['-entry_date']
        verbose_name_plural = "Truck Entries"

    def __str__(self):
        return f"{self.truck_number} - {self.status}"

    # 3. 🔥 NEW: The Interceptor
    def save(self, *args, **kwargs):
        # Before saving the truck, ensure this transporter exists in our permanent table.
        # get_or_create safely adds it if it's brand new, or ignores it if it already exists!
        if self.transporter_name:
            Transporter.objects.get_or_create(name=self.transporter_name.strip())
        if self.entry_date:
            self.entry_month = self.entry_date.strftime('%b-%Y').lower() 
            
        super().save(*args, **kwargs)