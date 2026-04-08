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
import traceback
from rest_framework.decorators import permission_classes,api_view
import time
from django.db import connection,OperationalError

User = get_user_model()

# =================================================================
# HELPER: Extract IP Address safely
# =================================================================
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

@api_view(['GET'])
@permission_classes([AllowAny])
def server_health_check(request):
    # If this responds, the server and DB are officially awake!
    return Response({"status": "awake", "message": "Server is ready"})

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
        try:
            refresh_token_str = request.data.get("refresh_token")
            
            if not refresh_token_str:
                print("🚨 REFRESH_ERROR: No refresh token provided in request body.")
                return Response({"detail": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)

            # 🔥 THE NEW IN-FLIGHT RETRY LOOP 🔥
            session = None
            for attempt in range(3):
                try:
                    # Attempt to hit the database
                    session = UserSession.objects.filter(refresh_token=refresh_token_str).first()
                    break  # If it succeeds, break out of the loop immediately!
                except OperationalError as e:
                    # If this was the last attempt, give up and let the 500 catcher handle it
                    if attempt == 2:
                        raise e
                    
                    print(f"⏳ Database asleep. Retrying in 2 seconds... (Attempt {attempt + 1}/3)")
                    connection.close()  # 🚨 CRITICAL: Destroy the broken connection
                    time.sleep(2)       # Wait 2 seconds for Postgres to finish booting

            
            if not session:
                print("🚨 REFRESH_ERROR: Token not found in database.")
                return Response({"detail": "Session not found."}, status=status.HTTP_401_UNAUTHORIZED)

            # Helper to try and grab the email early for error logging if the session has a user_id
            session_user_id = getattr(session, 'user_id', None)
            user_email = "Unknown"
            if session_user_id:
                # (Since the retry loop above succeeded, we know the DB is fully awake for this query)
                user = User.objects.filter(user_id=session_user_id).first()
                if user:
                    user_email = user.email

            now = timezone.now()
            if session.expires_at <= now:
                print(f"🚨 REFRESH_ERROR: Session expired in database for user: {user_email}")
                session.delete()
                return Response({"detail": "Session has expired in database."}, status=status.HTTP_401_UNAUTHORIZED)

            try:
                refresh = CustomRefreshToken(refresh_token_str)
                token_user_id = refresh.payload.get('user_id')
                
                # Fetch user again via JWT payload just to be perfectly secure
                user = User.objects.filter(user_id=token_user_id).first()
                
                if not user or not user.is_active:
                    email = user.email if user else "Unknown"
                    print(f"🚨 REFRESH_ERROR: Account blocked or missing for user: {email}")
                    session.delete()
                    return Response(
                        {"detail": "Session terminated. Account has been blocked.", "code": "account_blocked"},
                        status=status.HTTP_403_FORBIDDEN
                    )

                access_token = str(refresh.access_token)
                
                # The only non-error print you care about
                print(f"✅ REFRESH_SUCCESS: Token refreshed for {user.email}")

                return Response({
                    "detail": "Access token refreshed",
                    "access_token": access_token
                }, status=status.HTTP_200_OK)

            except Exception as jwt_e:
                print(f"🚨 REFRESH_ERROR: JWT decoding failed for user: {user_email} | Error: {str(jwt_e)}")
                session.delete()
                return Response({"detail": f"Invalid refresh token: {str(jwt_e)}"}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as critical_e:
            # The true 500 error catcher. We keep the traceback so you actually know what broke.
            print(f"💥 FATAL 500 CRASH IN REFRESH_TOKEN | Error: {str(critical_e)}")
            traceback.print_exc()  
            
            return Response(
                {"detail": "An unexpected server error occurred during token refresh."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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