from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import random
from django.core.mail import send_mail

# ----------------- Profile -----------------
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


# ----------------- User -----------------
class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.email


# ----------------- Email Verification -----------------
class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['email']),
        ]

    def is_expired(self):
         
        return False

    def __str__(self):
        return f"{self.email} - {self.verification_code}"

    # Генерация 6-значного кода
    @staticmethod
    def generate_code():
        return f"{random.randint(100000, 999999)}"

    # Отправка кода (для dev вывод в консоль)
    def send_code(self):
        subject = "Your verification code"
        message = f"Your verification code is: {self.verification_code}"
        from_email = None  # будет использован DEFAULT_FROM_EMAIL
        recipient_list = [self.email]
        send_mail(subject, message, from_email, recipient_list)
