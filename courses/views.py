# courses/views.py — ФИНАЛЬНАЯ ВЕРСИЯ 
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters
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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']           # ← поиск по названию и описанию
    ordering_fields = ['start_time', 'title', 'enrolled_count']
    ordering = ['start_time']


# ==================== ДЕТАЛЬНЫЙ КУРС (с модулями, прогрессом) ====================
class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Course.objects.filter(start_time__lte=timezone.now())
          

    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Course.DoesNotExist:
            # Проверяем, существует ли курс вообще, но ещё не начался
            try:
                course = Course.objects.get(pk=kwargs['pk'])
                if course.start_time > timezone.now():
                    return Response(
                        {
                            "detail": "Курс ещё не начался. Доступ будет открыт после даты начала.",
                            "start_time": course.start_time,
                            "title": course.title
                        },
                        status=status.HTTP_200_OK
                    )
            except Course.DoesNotExist:
                pass  # действительно не существует

            return Response(
                {"detail": "Курс не найден."},
                status=status.HTTP_404_NOT_FOUND
            )
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
# courses/views.py  
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
