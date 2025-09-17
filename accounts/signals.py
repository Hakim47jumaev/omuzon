from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Profile, User
import os

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(post_delete, sender=Profile)
def delete_avatar_on_user_delete(sender, instance, **kwargs):
    if instance.avatar and os.path.isfile(instance.avatar.path):
        os.remove(instance.avatar.path)
