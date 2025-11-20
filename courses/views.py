# courses/views.py — ФИНАЛЬНАЯ ВЕРСИЯ (копируй целиком)
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Course, Module, Task, Enrollment
from .serializers import (
    LightCourseSerializer,        # ← новый лёгкий
    DetailedCourseSerializer,      # ← новый тяжёлый с модулями и прогрессом
    TaskSerializer,
    ModuleSerializer,
    EnrollmentSerializer
)


# ==================== ПЕРМИШЕНЫ ====================
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'owner', None) == request.user


# ==================== СПИСОК КУРСОВ (лёгкий, без задач) ====================
class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = LightCourseSerializer
    permission_classes = [permissions.AllowAny]


# ==================== ДЕТАЛЬНЫЙ КУРС (с модулями, прогрессом) ====================
class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        return DetailedCourseSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# ==================== МОИ КУРСЫ (лёгкие) ====================
class MyEnrolledCoursesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        courses = Course.objects.filter(enrollments__user=request.user)
        serializer = LightCourseSerializer(courses, many=True)
        return Response(serializer.data)


# ==================== ДЕТАЛЬ МОДУЛЯ ====================
class ModuleDetailView(generics.RetrieveAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.AllowAny]


# ==================== ДЕТАЛЬ ЗАДАЧИ ====================
class TaskDetailView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.AllowAny]


# ==================== ЗАПИСЬ НА КУРС ====================
# courses/views.py — замени только этот класс
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class EnrollView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['course_id'],
            properties={
                'course_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID курса, на который хочешь записаться'
                )
            }
        ),
        responses={
            201: openapi.Response('Успешно записан'),
            200: openapi.Response('Уже записан'),
            400: 'course_id обязателен',
            404: 'Курс не найден'
        }
    )
    def post(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )

        if created:
            return Response(
                {'message': 'Успешно записан на курс'},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Вы уже записаны на этот курс'},
            status=status.HTTP_200_OK
        )
    # ==================== АДМИНСКИЕ ВЬЮХИ (создание/редактирование) ====================
class CourseCreateView(generics.CreateAPIView):
    queryset = Course.objects.all()
    serializer_class = LightCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CourseUpdateView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = LightCourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class CourseDeleteView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = LightCourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
