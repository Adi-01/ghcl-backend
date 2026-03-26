import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # =================================================================
    # CORE IDENTIFIER (API SAFE)
    # =================================================================
    user_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )

    # =================================================================
    # AUTH FIELDS
    # =================================================================
    email = models.EmailField(unique=True, db_index=True)

    username = models.CharField(
        max_length=150,
        blank=True,
        null=True 
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # =================================================================
    # LABELS
    # =================================================================
    labels = models.JSONField(
        default=list,
        blank=True
    )
    # Example:
    # ["admin", "moderator", "owner"]

    # =================================================================
    # TIMESTAMPS
    # =================================================================
    updated_at = models.DateTimeField(auto_now=True)

    # =================================================================
    # DJANGO CONFIG
    # =================================================================
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()  # <- use custom manager 

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class UserSession(models.Model):
    # =================================================================
    # CORE IDENTIFIERS
    # =================================================================
    # We use a UUID so if we ever pass the session ID to the frontend 
    # (e.g., to click "Revoke Device"), it is API-safe and unguessable.
    session_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True, 
        primary_key=True
    )
    
    # Link to the user. If the user is deleted, their sessions are deleted (CASCADE).
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="active_sessions",
        db_index=True
    )
    
    # We store the exact refresh token string. 
    # db_index=True makes looking up the token lightning fast during the refresh cycle.
    refresh_token = models.TextField(unique=True, db_index=True)

    # =================================================================
    # DEVICE AUDIT INFO (For the Frontend UI)
    # =================================================================
    # Will store parsed User-Agent (e.g., "Chrome on Mac", "Safari on iPhone")
    device_info = models.CharField(max_length=255, blank=True, null=True)
    
    # Will store the IP address (e.g., "192.168.1.1")
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    # =================================================================
    # LIFECYCLE TIMESTAMPS
    # =================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    
    # We will explicitly set this to 7 days in the future when creating the session.
    # This allows us to easily filter out mathematically dead tokens.
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        # Most recent logins show up first
        ordering = ['-created_at']
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"{self.user.email} | {self.device_info} | {self.ip_address}"
    
    @property
    def is_expired(self):
        """Helper property to quickly check if the session has naturally died."""
        from django.utils import timezone
        return timezone.now() > self.expires_at