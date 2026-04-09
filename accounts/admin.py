from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserSession

# --- Inline for User Sessions ---
class UserSessionInline(admin.TabularInline):
    model = UserSession
    extra = 0  # Prevents empty rows from showing up
    # 🔥 CHANGED: refresh_token -> session_token
    readonly_fields = ("session_id", "device_info", "ip_address", "created_at", "expires_at", "session_token")
    can_delete = True  # Allows you to "Revoke" a session by deleting it here
    fields = ("device_info", "ip_address", "created_at", "expires_at")

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    inlines = [UserSessionInline] # <--- Displays active devices on user edit page
    
    list_display = (
        "email",
        "username",
        "phone_number",
        "is_active",
        "is_staff",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    list_filter = ("is_active", "is_staff")
    ordering = ("email",)
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("username", "phone_number")}),
        ("Labels", {"fields": ("labels",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Timestamps", {"fields": ("last_login", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password"), # Adjusted to match standard create
            },
        ),
    )

    search_fields = ("email",)

# --- Standalone Session Admin ---
@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_info", "ip_address", "created_at", "is_expired")
    list_filter = ("created_at", "expires_at")
    search_fields = ("user__email", "ip_address", "device_info")
    # 🔥 CHANGED: refresh_token -> session_token
    readonly_fields = ("session_id", "created_at", "session_token")