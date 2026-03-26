from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from .models import User
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "user_id",
            "email",
            "username",
            "phone_number",
            "labels",
            "is_active",
            "updated_at",
            "date_joined"
        ]
        read_only_fields = ["user_id", "updated_at", "date_joined"]


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "username", "phone_number"]

    def validate_email(self, email):
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Account already exists")
        return email

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            username=validated_data.get("username"),
            phone_number=validated_data.get("phone_number"),
        )



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if email and password:
            # 1. Manually fetch the user by email
            user_obj = User.objects.filter(email=email).first()
            
            if user_obj:
                # 2. Check if the password is correct
                if user_obj.check_password(password):
                    
                    # 3. INTERCEPT BLOCKED USERS HERE
                    if not user_obj.is_active:
                        # PermissionDenied automatically returns a 403 Forbidden status
                        raise PermissionDenied(
                            detail="Your account has been blocked by an administrator.", 
                            code="account_blocked"
                        )
                    
                    # If active and password is correct, attach user to validated_data
                    data["user"] = user_obj
                    return data

        # If email doesn't exist or password is wrong, return the generic error
        raise serializers.ValidationError("Invalid email or password.")




class AdminUserSerializer(serializers.ModelSerializer):
    # Make password write-only so it never gets sent back to the frontend
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'user_id', 'email', 'username', 'phone_number', 
            'labels', 'is_active', 'is_staff', 'date_joined', 'updated_at', 'password',
        ]
        # Remove 'email' from read_only_fields so we can set it during creation
        read_only_fields = ['user_id', 'date_joined', 'updated_at']

    def validate_labels(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Labels must be a list.")
        return [str(label).strip().lower() for label in value if str(label).strip()]

    def create(self, validated_data):
        # Safely extract the password before saving the model
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password) # This hashes it!
        user.save()
        return user