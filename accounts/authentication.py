from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import UserSession

class OpaqueTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None 

        token = auth_header.split(' ')[1]

        session = UserSession.objects.filter(session_token=token).select_related('user').first()

        if not session:
            raise AuthenticationFailed("Invalid or expired session.")

        if session.expires_at < timezone.now():
            session.delete()
            raise AuthenticationFailed("Session has expired.")

        return (session.user, token)

    # 🔥 NEW: Add this to fix the 403 vs 401 issue!
    def authenticate_header(self, request):
        return 'Bearer'