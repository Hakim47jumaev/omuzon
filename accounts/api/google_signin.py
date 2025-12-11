from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from rest_framework_simplejwt.tokens import RefreshToken

# Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


User = get_user_model()


# ---- Serializer ----
class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    email = serializers.EmailField()
    display_name = serializers.CharField(required=False)


# ---- API View ----
class GoogleSignInAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=GoogleSignInSerializer,
        responses={200: openapi.Response("Google Sign-In successful")},
        operation_description="Sign in using Google ID token. Returns JWT access and refresh tokens."
    )
    def post(self, request):
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_token_str = serializer.validated_data["id_token"]
        email_from_frontend = serializer.validated_data["email"]
        display_name = serializer.validated_data.get("display_name", "")

        # --- Google token verify ---
        try:
            info = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            google_email = info.get("email")
            google_name = info.get("name", "")
            google_sub = info.get("sub")  # unique Google ID

            # email mismatch protection
            if google_email != email_from_frontend:
                return Response({"detail": "Email mismatch"}, status=400)

        except Exception:
            return Response({"detail": "Invalid Google token"}, status=400)

        # --- Create or login user ---
        user, created = User.objects.get_or_create(
            email=google_email,
            defaults={
                "username": google_email,
                "first_name": display_name or google_name,
            }
        )

        # --- JWT tokens ---
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.first_name,
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }
        }, status=200)
