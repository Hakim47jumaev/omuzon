from django.db import models
from django.conf import settings
from django.utils import timezone


# ----------------- Course -----------------
class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    show = models.BooleanField(default=True)
    is_exam=models.BooleanField(default=False)
    is_olimpiad = models.BooleanField(default=False)
    end_time = models.DateTimeField(null=True, blank=True)

    @property
    def enrolled_count(self):
        return self.enrollments.count()
    
    @property
    def is_active(self):
        return self.start_time is not None and self.start_time <= timezone.now()
    
    @property
    def is_olimpiad_active(self):
        """Проверяет, активна ли олимпиада в данный момент"""
        if not self.is_olimpiad:
            return False
        now = timezone.now()
        if self.start_time and self.start_time > now:
            return False
        if self.end_time and self.end_time < now:
            return False
        return True
    
    @property
    def is_olimpiad_finished(self):
        """Проверяет, закончилась ли олимпиада"""
        if not self.is_olimpiad:
            return False
        if self.end_time:
            return timezone.now() > self.end_time
        return False
    
    def __str__(self):
        return self.title

# ----------------- Module -----------------
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        ordering = ['order']


# ----------------- Task -----------------
class Task(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_text = models.TextField()  # текст задачи
    order = models.PositiveIntegerField(default=1)
    show_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    class Meta:
        ordering = ['order']

    


# ----------------- Enrollment -----------------
class Enrollment(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    progress = models.FloatField(default=0.0)

    # --- НОВОЕ ---
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )
     

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.status})"




class TestCase(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='testcases')
    input_data = models.TextField(blank=True)        
    expected_output = models.TextField()    
    is_active = models.BooleanField(default=True)   
    order = models.PositiveIntegerField(default=1)  

    def __str__(self):
        return f"TestCase {self.id} for {self.task.title}"

    class Meta:
        ordering = ['order']