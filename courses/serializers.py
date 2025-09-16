from rest_framework import serializers
from .models import Course, Module, Task, Enrollment
from accounts.models import User  # если понадобится сериализация юзера


# ----------------- Task Serializer -----------------
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'task_text', 'order']


# ----------------- Module Serializer -----------------
class ModuleSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'tasks']


# ----------------- Course Serializer -----------------
class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()
    enrolled_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'start_time', 'is_active', 'modules', 'enrolled_count']


# ----------------- Enrollment Serializer -----------------
class EnrollmentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    course = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course', 'enrolled_at', 'progress']
