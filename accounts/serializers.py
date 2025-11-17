# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import EmailVerification, Profile
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from django.db import models

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        if EmailVerification.objects.filter(email=value, is_used=False).exists():
            raise serializers.ValidationError("Check your email — code already sent.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is taken.")
        return value

    def create(self, validated_data):
        EmailVerification.objects.filter(email=validated_data['email']).delete()

        code = EmailVerification.generate_code()
        ev = EmailVerification.objects.create(
            email=validated_data['email'],
            verification_code=code,
            temp_username=validated_data['username'],
            temp_password=validated_data['password'],  # ← ЧИСТЫЙ ПАРОЛЬ!
            created_at=timezone.now(),
        )
        ev.send_code()
        return ev


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=4)

    def validate(self, attrs):
        try:
            ev = EmailVerification.objects.get(
                email=attrs['email'],
                verification_code=attrs['verification_code'],
                is_used=False
            )
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired code.")

        if ev.is_expired():
            raise serializers.ValidationError("Verification code has expired.")

        attrs['email_verification'] = ev
        return attrs

# accounts/serializers.py
    def create(self, validated_data):
            ev = validated_data['email_verification']

            user = User.objects.create_user(
                username=ev.temp_username,
                email=ev.email,
                password=None  # не передаём
            )
            user.set_password(ev.temp_password)  # ← правильный хэш
            user.save()

            ev.is_used = True
            ev.temp_username = ''
            ev.temp_password = ''
            ev.save()

            return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login = attrs['login']
        password = attrs['password']

        try:
            # Ищем пользователя по username ИЛИ email
            user = User.objects.get(
                models.Q(username=login) | models.Q(email__iexact=login)
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid login or password.")

        # Проверяем пароль напрямую — это 100% работает
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid login or password.")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")

        attrs['user'] = user
        return attrs

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Profile
        fields = ['id', 'user', 'avatar', 'bio']
        read_only_fields = ['id', 'user']