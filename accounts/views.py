from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import logout
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import (
    RegisterSerializer,
    VerifyCodeSerializer,
    LoginSerializer,
    UserSerializer
)


# ----------------- Register -----------------
class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # отправка кода на email
        return Response({"message": "Verification code sent to email"}, status=status.HTTP_200_OK)


# ----------------- Verify -----------------
class VerifyCodeView(generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "User created successfully",
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


# ----------------- Login -----------------
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)


# ----------------- Logout -----------------
class LogoutView(APIView):
    """
    Для JWT logout — обычно на клиенте просто удаляем токены.
    Если используется blacklist, можно реализовать аннулирование refresh токена.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({"message": "Logged out (client should discard JWT)"}, status=status.HTTP_200_OK)



from rest_framework import generics, permissions
from .models import Profile
from .serializers import ProfileSerializer

# ----------------- Profile -----------------
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes=[MultiPartParser,FormParser]

    def get_object(self):
        # всегда возвращаем профиль текущего юзера
        return self.request.user.profile