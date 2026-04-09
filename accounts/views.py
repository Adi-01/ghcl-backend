import secrets # 🔥 NEW: For generating secure opaque tokens
from datetime import timedelta
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, UserSession
from .serializers import LoginSerializer, AdminUserSerializer
from .permissions import IsAdminUser
from rest_framework.decorators import permission_classes, api_view

User = get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

@api_view(['GET'])
@permission_classes([AllowAny])
def server_health_check(request):
    return Response({"status": "awake", "message": "Server is ready"})

class AuthViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet-based user side auth:
    - POST /auth/login/
    - POST /auth/logout/
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
        
        if active_sessions.count() >= 1:
            session = active_sessions.first()
            return Response(
                {
                    "detail": "Account in use on another device. Please use that device or contact an administrator to revoke the existing session.",
                    "code": "device_limit_reached",
                    "device_info": session.device_info, 
                    "ip_address": session.ip_address
                }, 
                status=status.HTTP_409_CONFLICT
            )

        # 🔥 NEW: Generate a 64-character secure random string
        opaque_token = secrets.token_urlsafe(64)

        # Create the new session tracker
        UserSession.objects.create(
            user=user,
            session_token=opaque_token, # Use the new token
            device_info=request.META.get('HTTP_USER_AGENT', 'Unknown Device')[:255],
            ip_address=get_client_ip(request),
            expires_at=timezone.now() + timedelta(days=7)
        )

        return Response({
            "session_token": opaque_token,
            "roles": user.labels # Pass roles to frontend for routing
        }, status=status.HTTP_200_OK)


    # 🔥 DELETED refresh_token METHOD COMPLETELY 🔥


    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="logout")
    def logout(self, request):
        session_token = request.data.get("session_token")
        
        print("\n" + "="*50)
        print("🚨 LOGOUT ENDPOINT CALLED 🚨")
        print(f"Token provided in request body: {'YES' if session_token else 'NO'}")
        
        if session_token:
            try:
                session = UserSession.objects.filter(session_token=session_token).first()
                if session:
                    print(f"✅ Session found in DB for user_id {session.user_id}. Deleting now...")
                    session.delete()
                else:
                    print("⚠️ Session was NOT found in DB. It was already deleted somehow!")
            except Exception as e:
                print(f"⚠️ Error during delete process: {str(e)}")
                
        print("="*50 + "\n")
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

    @action(detail=True, methods=["get"], url_path="sessions")
    def get_sessions(self, request, user_id=None):
        user = self.get_object()
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
        user = self.get_object()
        session_id = request.data.get("session_id")
          
        if not session_id:
            return Response({"detail": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        session = UserSession.objects.filter(user=user, session_id=session_id).first()
        
        if not session:
            return Response({"detail": "Session not found or already expired."}, status=status.HTTP_404_NOT_FOUND)

        session.delete()
        return Response({"detail": "Device session successfully revoked."}, status=status.HTTP_200_OK)