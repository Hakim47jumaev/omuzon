from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Task   

User = get_user_model()

class Submission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
        ('error', 'Ошибка'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    code = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True)
    errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} → {self.task.title}"