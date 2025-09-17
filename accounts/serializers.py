from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import EmailVerification ,Profile

User = get_user_model()

# ----------------- Register -----------------
class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def create(self, validated_data):
        code = EmailVerification.generate_code()
        ev, _ = EmailVerification.objects.update_or_create(
            email=validated_data['email'],
            defaults={'verification_code': code, 'is_used': False}
        )
        ev.send_code()
        return ev


# ----------------- Verify -----------------
class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=6)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            ev = EmailVerification.objects.get(email=attrs['email'], is_used=False)
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("No verification code found or already used")

        if ev.verification_code != attrs['verification_code']:
            raise serializers.ValidationError("Invalid verification code")

        if ev.is_expired():
            raise serializers.ValidationError("Verification code expired")

        attrs['email_verification'] = ev
        return attrs

    def create(self, validated_data):
        ev = validated_data.pop('email_verification')
        username = validated_data.get('username') or validated_data['email'].split('@')[0]

        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=validated_data['password']
        )

        ev.is_used = True
        ev.save()

        return user


# ----------------- User Serializer -----------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']


# ----------------- Login Serializer -----------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')
        password = attrs.get('password')

        if not email and not username:
            raise serializers.ValidationError("Provide either email or username")

        # Аутентификация через email или username
        if email:
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid credentials")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        attrs['user'] = user
        return attrs


  

class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # будет показывать username

    class Meta:
        model = Profile
        fields = ['id', 'user', 'avatar', 'bio']
