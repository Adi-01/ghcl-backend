from datetime import timedelta
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .tokens import CustomRefreshToken
from .models import User, UserSession
from .serializers import LoginSerializer, AdminUserSerializer
from .permissions import IsAdminUser

User = get_user_model()

# =================================================================
# HELPER: Extract IP Address safely
# =================================================================
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

class AuthViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet-based user side auth:
    - POST /auth/signup/
    - POST /auth/login/
    - POST /auth/logout/
    - POST /auth/refresh/
    """
    queryset = User.objects.none()
    permission_classes = [AllowAny]
    http_method_names = ["post"]

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # ENFORCE STRICT 1-DEVICE LIMIT
        active_sessions = user.active_sessions.filter(expires_at__gt=timezone.now())
        
        # If there is 1 or more active sessions, block the login
        if active_sessions.count() >= 1:
            session = active_sessions.first()
            return Response(
                {
                    "detail": "Account in use on another device. Please use that device or contact an administrator to revoke the existing session.",
                    "code": "device_limit_reached",
                    "device_info": session.device_info, # Provide info so they know where they are logged in
                    "ip_address": session.ip_address
                }, 
                status=status.HTTP_409_CONFLICT
            )

        refresh = CustomRefreshToken.for_user(user)

        # Create the new session tracker
        UserSession.objects.create(
            user=user,
            refresh_token=str(refresh),
            device_info=request.META.get('HTTP_USER_AGENT', 'Unknown Device')[:255],
            ip_address=get_client_ip(request),
            expires_at=timezone.now() + timedelta(days=7)
        )

        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }, status=status.HTTP_200_OK)


    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="refresh")
    def refresh_token(self, request):
        refresh_token_str = request.data.get("refresh_token")
        
        if not refresh_token_str:
            print("🚨 REFRESH_DEBUG: No token provided in request body.")
            return Response({"detail": "No refresh token provided"}, status=status.HTTP_401_UNAUTHORIZED)

        # 1. Look for the session record without the time filter first
        session = UserSession.objects.filter(refresh_token=refresh_token_str).first()
        
        if not session:
            print(f"🚨 REFRESH_DEBUG: Token string not found in UserSession table. Length of string sent: {len(refresh_token_str)}")
            return Response({"detail": "Session not found."}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Check the expiration logic
        now = timezone.now()
        if session.expires_at <= now:
            print(f"🚨 REFRESH_DEBUG: DB Expiry Check Failed.")
            print(f"   - Current Server Time (UTC): {now}")
            print(f"   - DB Session Expiry (UTC):   {session.expires_at}")
            print(f"   - Time Difference:           {session.expires_at - now}")
            
            # Since this session is dead in the DB, clean it up so the user isn't locked out!
            session.delete()
            return Response({"detail": "Session has expired in database."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # 3. Attempt JWT Decoding
            refresh = CustomRefreshToken(refresh_token_str)
            token_user_id = refresh.payload.get('user_id')
            
            user = User.objects.filter(user_id=token_user_id).first()
            
            if not user or not user.is_active:
                print(f"🚨 REFRESH_DEBUG: User {token_user_id} is inactive or does not exist. Deleting session.")
                session.delete()
                return Response(
                    {"detail": "Session terminated. Account has been blocked.", "code": "account_blocked"},
                    status=status.HTTP_403_FORBIDDEN
                )

            access_token = str(refresh.access_token)
            print(f"✅ REFRESH_DEBUG: Success for user {user.email}")

        except Exception as e:
            # 4. JWT Math Error (Expired signature, wrong secret key, etc.)
            print(f"🚨 REFRESH_DEBUG: SimpleJWT Exception caught!")
            print(f"   - Error Type: {type(e).__name__}")
            print(f"   - Error Message: {str(e)}")
            
            # IMPORTANT: If the JWT is dead, the session is dead. 
            # Delete it so the user can log back in on the login screen.
            # session.delete()
            return Response({"detail": f"Invalid refresh token: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "detail": "Access token refreshed",
            "access_token": access_token
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="logout")
    def logout(self, request):
        refresh_token = request.data.get("refresh_token")

        if refresh_token:
            try:
                UserSession.objects.filter(refresh_token=refresh_token).delete()

                token = CustomRefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)

class AdminUserViewSet(viewsets.ModelViewSet):
    """
    Full CRUD ViewSet for Admins to manage users.
    """
    permission_classes = [IsAdminUser] 
    serializer_class = AdminUserSerializer
    lookup_field = 'user_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['email', 'username', 'phone_number']
    filterset_fields = ['is_active']

    def get_queryset(self):
        return User.objects.filter(is_superuser=False).order_by('-date_joined')

    # =========================================================
    # NEW: Admin Session Management
    # =========================================================
    
    @action(detail=True, methods=["get"], url_path="sessions")
    def get_sessions(self, request, user_id=None):
        """
        GET /admin-users/<user_id>/sessions/
        Returns a list of all active devices for a specific user.
        """
        user = self.get_object()
        # Only fetch living sessions
        active_sessions = user.active_sessions.filter(expires_at__gt=timezone.now())
        
        data = [
            {
                "session_id": str(s.session_id),
                "device_info": s.device_info,
                "ip_address": s.ip_address,
                "created_at": s.created_at,
            }
            for s in active_sessions
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="revoke-session")
    def revoke_session(self, request, user_id=None):
        """
        POST /admin-users/<user_id>/revoke-session/
        Body: {"session_id": "uuid-string"}
        Instantly kills a specific device for a user.
        """
        user = self.get_object()
        session_id = request.data.get("session_id")
          
        if not session_id:
            return Response({"detail": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Find the session record
        session = UserSession.objects.filter(user=user, session_id=session_id).first()
        
        if not session:
            return Response({"detail": "Session not found or already expired."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Blacklist the token so it can NEVER be used again anywhere
        try:
            token = CustomRefreshToken(session.refresh_token)
            token.blacklist()
        except Exception as e:
            # If the token is already expired or malformed, blacklisting might fail
            # We continue anyway because we want the DB record gone
            pass

        # 3. Delete the session from the database
        session.delete()
        
        return Response({"detail": "Device session successfully revoked."}, status=status.HTTP_200_OK)