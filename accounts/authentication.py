# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import UserSession

class OpaqueTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None # Move on to next auth class or fail

        token = auth_header.split(' ')[1]

        # 🚨 THE INSTANT KILL CHECK: Does this token exist in the DB right now?
        session = UserSession.objects.filter(session_token=token).select_related('user').first()

        if not session:
            raise AuthenticationFailed("Invalid or expired session.")

        if session.expires_at < timezone.now():
            session.delete()
            raise AuthenticationFailed("Session has expired.")

        # Return the user and the token (makes request.user work perfectly in views)
        return (session.user, token)