from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("jwt_access")
        if not token:
            return None
        validated_token = self.get_validated_token(token)
        user = self.get_user(validated_token)
        return (user, validated_token)
