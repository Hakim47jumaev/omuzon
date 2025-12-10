# accounts/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    RegisterSerializer, VerifyCodeSerializer,
    LoginSerializer, UserSerializer, ProfileSerializer
)
from .models import EmailVerification


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Verification code sent to your email."})

 
class VerifyCodeView(generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()  # ← пользователь создан

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Account created successfully.",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user.profile


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out."})


# РЕСЕНД КОДА
class ResendCodeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            ev = EmailVerification.objects.get(email=email, is_used=False)
            ev.verification_code = EmailVerification.generate_code()
            ev.created_at = timezone.now()
            ev.save()
            ev.send_code()
            return Response({"message": "New verification code sent."})
        except EmailVerification.DoesNotExist:
            return Response({"error": "No pending registration for this email."}, status=400)