from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Course, Module, Task, Enrollment
from .serializers import CourseSerializer, ModuleSerializer, TaskSerializer, EnrollmentSerializer

# ----------------- Custom Permission -----------------
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешает изменение объекта только владельцу.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'owner', None) == request.user


# ----------------- Courses -----------------
class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]


class CourseCreateView(generics.CreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CourseUpdateView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class CourseDeleteView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


# ----------------- Modules -----------------
class ModuleDetailView(generics.RetrieveAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.AllowAny]


class ModuleCreateView(generics.CreateAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Owner берётся от курса
        course_id = self.request.data.get('course')
        course = get_object_or_404(Course, id=course_id)
        if course.owner != self.request.user:
            raise permissions.PermissionDenied("You are not the owner of this course.")
        serializer.save(course=course)


class ModuleUpdateView(generics.UpdateAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class ModuleDeleteView(generics.DestroyAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


# ----------------- Tasks -----------------
class TaskDetailView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.AllowAny]


class TaskCreateView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Owner берётся от модуля через курс
        module_id = self.request.data.get('module')
        module = get_object_or_404(Module, id=module_id)
        if module.course.owner != self.request.user:
            raise permissions.PermissionDenied("You are not the owner of this course.")
        serializer.save(module=module)


class TaskUpdateView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class TaskDeleteView(generics.DestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class EnrollView(APIView):
    """
    Запись студента на курс
    POST /enroll/
    {
        "course_id": 5
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    # Красивая схема для Swagger
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['course_id'],
            properties={
                'course_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID курса, на который хотите записаться'
                )
            }
        ),
        responses={
            201: openapi.Response(
                description='Успешно записан на курс',
                schema=EnrollmentSerializer()
            ),
            200: openapi.Response(
                description='Вы уже записаны на этот курс',
                examples={'application/json': {'message': 'You are already enrolled in this course'}}
            ),
            400: 'course_id обязателен',
            404: 'Курс не найден'
        },
        operation_description="Записывает текущего пользователя на курс. Если уже записан — возвращает 200 с сообщением."
    )
    def post(self, request):
        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {'error': 'course_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, существует ли курс
        course = get_object_or_404(Course, id=course_id)

        # Пытаемся создать запись
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )

        serializer = EnrollmentSerializer(enrollment)

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'message': 'You are already enrolled in this course'},
                status=status.HTTP_200_OK
            )
class MyEnrolledCoursesView(APIView):
    """
    Список курсов, на которые пользователь записан
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        enrollments = Enrollment.objects.filter(user=user)
        courses = [enrollment.course for enrollment in enrollments]
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
