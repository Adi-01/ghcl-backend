from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # 1. BEST PRACTICE: Check for standard Authorization Bearer header first
        # This is how Next.js Server Actions will communicate securely with Django
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return (self.get_user(validated_token), validated_token)

        # 2. FALLBACK: Check the cookies 
        # (Useful if you ever hit the API directly from the browser)
        raw_token = request.COOKIES.get("access_token")
        if raw_token is not None:
            try:
                validated_token = self.get_validated_token(raw_token)
                return (self.get_user(validated_token), validated_token)
            except Exception:
                return None # Token is invalid or expired

        return None # No token found