# courses/serializers.py
from rest_framework import serializers
from .models import Course, Module, Task, Enrollment
from submissions.models import Submission  # ← важно для подсчёта решённых задач


# ===================== ЛЁГКИЙ СЕРИАЛИЗАТОР ДЛЯ СПИСКОВ =====================
class LightCourseSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.IntegerField(read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'start_time',
            'is_active',
            'enrolled_count'
        ]


# ===================== ЗАДАЧА =====================
class TaskSerializer(serializers.ModelSerializer):
    is_solved = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'task_text', 'order', 'is_solved']

    def get_is_solved(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return Submission.objects.filter(
            user=user,
            task=obj,
            status='accepted'
        ).exists()

# ===================== МОДУЛЬ С ЗАДАЧАМИ =====================
class ModuleSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'tasks']


# ===================== ПОЛНЫЙ КУРС С ПРОГРЕССОМ =====================
class DetailedCourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    solved_tasks_count = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'start_time',
            'is_enrolled',
            'solved_tasks_count',
            'total_tasks',
            'progress_percent',
            'modules'
        ]

    def get_is_enrolled(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False

    def get_solved_tasks_count(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return 0
        return Submission.objects.filter(
            user=user,
            task__module__course=obj,
            status='accepted'  # ← у тебя в модели Submission есть поле status
        ).values('task').distinct().count()

    def get_total_tasks(self, obj):
        return Task.objects.filter(module__course=obj).count()

    def get_progress_percent(self, obj):
        total = self.get_total_tasks(obj)
        if total == 0:
            return 0
        solved = self.get_solved_tasks_count(obj)
        return round((solved / total) * 100, 1)


# ===================== ЗАПИСЬ НА КУРС =====================
class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'enrolled_at', 'progress']