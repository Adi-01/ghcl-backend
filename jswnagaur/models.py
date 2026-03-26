import string
from django.db import models
from django.utils.crypto import get_random_string

class JswSupplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.name

def generate_entry_id():
    """Generates a secure, random 16-character alphanumeric string."""
    allowed_chars = string.ascii_letters + string.digits
    return get_random_string(length=16, allowed_chars=allowed_chars)

class JswNagaurEntry(models.Model):
    # Auto-generated 16-character ID, non-editable so it stays secure
    entry_id = models.CharField(
        max_length=16, 
        unique=True, 
        default=generate_entry_id, 
        editable=False
    )
    
    # Using CharField for Serial Number in case it includes letters like "SN-001"
    serial_number = models.IntegerField(db_index=True)
    truck_number = models.CharField(max_length=50)
    
    # New Fields
    invoice_number = models.CharField(max_length=100)
    remarks = models.TextField(blank=True, null=True) # Optional text field
    
    # Decimal field perfect for Metric Tons (e.g., 45.500)
    metric = models.DecimalField(max_digits=10, decimal_places=3)
    
    seal_number = models.CharField(max_length=100)
    
    # PROTECT ensures you can't accidentally delete a supplier if trucks are tied to them
    supplier = models.ForeignKey(JswSupplier, on_delete=models.PROTECT, related_name='jsw_entries')
    
    entry_date = models.DateField()
    
    # We leave this blank=True because our save() method will auto-fill it
    entry_month = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "JSW Nagaur Entries"
        ordering = ['-entry_date', '-serial_number']

    def save(self, *args, **kwargs):
        # Automatically generate the month string (e.g., "mar-2026") from the date
        if self.entry_date:
            self.entry_month = self.entry_date.strftime('%b-%Y').lower() 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.serial_number} - {self.truck_number}"