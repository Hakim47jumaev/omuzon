# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import random
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from datetime import timedelta
from zoneinfo import ZoneInfo


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            base = self.email.split('@')[0]
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}_{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.email


class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=4)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    temp_username = models.CharField(max_length=150, blank=True)
    temp_password = models.CharField(max_length=128, blank=True)

    class Meta:
        indexes = [models.Index(fields=['email'])]

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @staticmethod
    def generate_code():
        return f"{random.randint(1000, 9999):04d}"

    def send_code(self):
        local_time = timezone.localtime(self.created_at, ZoneInfo("Asia/Dushanbe"))
        expires_at = local_time + timedelta(minutes=10)

        subject = "Your Verification Code"
        message = (
            f"Verification Code: {self.verification_code}\n\n"
            f"Sent at: {local_time.strftime('%H:%M, %d %B %Y')}\n"
            f"Valid until: {expires_at.strftime('%H:%M')}\n"
            f"Time zone: Tajikistan (UTC+5)\n\n"
            f"If you didn't request this, ignore this email."
        )
        send_mail(subject, message, None, [self.email], fail_silently=False)