# courses/views.py — ФИНАЛЬНАЯ ВЕРСИЯ 
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import filters
from .models import Course, Module, Task, Enrollment
from submissions.models import Submission
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
        return Course.objects.filter(start_time__lte=timezone.now()).prefetch_related('modules__tasks')
          

    
    def retrieve(self, request, *args, **kwargs):
        from django.http import Http404
        now = timezone.now()
        try:
            instance = self.get_object()
        except Http404:
            try:
                course = Course.objects.get(pk=kwargs['pk'])
                # Проверка для олимпиадного режима
                if course.is_olimpiad:
                    if course.start_time and course.start_time > now:
                        return Response(
                            {
                                "detail": "Олимпиада ещё не началась. Доступ будет открыт после даты начала.",
                                "start_time": course.start_time,
                                "end_time": course.end_time,
                                "title": course.title,
                                "is_olimpiad": True
                            },
                            status=status.HTTP_200_OK
                        )
                    if course.end_time and course.end_time < now:
                        return Response(
                            {
                                "detail": "Олимпиада завершена. Результаты зафиксированы.",
                                "start_time": course.start_time,
                                "end_time": course.end_time,
                                "title": course.title,
                                "is_olimpiad": True,
                                "is_finished": True
                            },
                            status=status.HTTP_200_OK
                        )
                elif course.start_time > now:
                    return Response(
                        {
                            "detail": "Курс ещё не начался. Доступ будет открыт после даты начала.",
                            "start_time": course.start_time,
                            "title": course.title
                        },
                        status=status.HTTP_200_OK
                    )
            except Course.DoesNotExist:
                pass
            return Response({"detail": "Курс не найден."}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверка для олимпиадного режима после получения объекта
        if instance.is_olimpiad:
            if instance.start_time and instance.start_time > now:
                return Response(
                    {
                        "detail": "Олимпиада ещё не началась. Доступ будет открыт после даты начала.",
                        "start_time": instance.start_time,
                        "end_time": instance.end_time,
                        "title": instance.title,
                        "is_olimpiad": True
                    },
                    status=status.HTTP_200_OK
                )
            if instance.end_time and instance.end_time < now:
                return Response(
                    {
                        "detail": "Олимпиада завершена. Результаты зафиксированы.",
                        "start_time": instance.start_time,
                        "end_time": instance.end_time,
                        "title": instance.title,
                        "is_olimpiad": True,
                        "is_finished": True
                    },
                    status=status.HTTP_200_OK
                )

        submissions_map = {}
        if request.user.is_authenticated:
            subs = (
                Submission.objects.filter(user=request.user, task__module__course=instance)
                .select_related('task')
                .order_by('created_at')
            )
            # Для олимпиадного режима фильтруем по времени
            if instance.is_olimpiad:
                if instance.start_time:
                    subs = subs.filter(created_at__gte=instance.start_time)
                if instance.end_time:
                    subs = subs.filter(created_at__lte=instance.end_time)
            
            for s in subs:
                submissions_map.setdefault(s.task_id, []).append(s)

        base_context = self.get_serializer_context()
        base_context["user_submissions_by_task"] = submissions_map
        serializer = self.get_serializer(instance, context=base_context)
        return Response(serializer.data)
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


# ==================== ЛИДЕРБОРД ОЛИМПИАДЫ ====================
class OlimpiadLeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Лидерборд олимпиады",
                examples={
                    "application/json": {
                        "course": {
                            "id": 1,
                            "title": "Олимпиада по программированию",
                            "is_olimpiad": True,
                            "start_time": "2024-01-01T10:00:00Z",
                            "end_time": "2024-01-01T12:00:00Z"
                        },
                        "leaderboard": [
                            {
                                "rank": 1,
                                "user_id": 1,
                                "username": "user1",
                                "solved_count": 5,
                                "submission_count": 8,
                                "last_accepted_at": "2024-01-01T11:30:00Z"
                            }
                        ]
                    }
                }
            ),
            400: "Курс не является олимпиадой",
            404: "Курс не найден"
        }
    )
    def get(self, request, course_id):
        """
        Получить лидерборд олимпиады.
        Сортировка: больше решённых задач → меньше попыток → раньше последний ACCEPTED
        """
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {"error": "Курс не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not course.is_olimpiad:
            return Response(
                {"error": "Этот курс не является олимпиадой"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем всех пользователей, у которых есть сабмиты по задачам этого курса
        # Это более правильно для олимпиады - если кто-то отправил решение, он должен быть в лидерборде
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Получаем уникальных пользователей, у которых есть сабмиты по задачам курса
        # Django создаёт обратную связь с именем 'submission' (единственное число)
        users_with_submissions = User.objects.filter(
            submission__task__module__course=course
        ).distinct()
        
        leaderboard_data = []
        now = timezone.now()
        
        for user in users_with_submissions:
            # Получаем все сабмиты пользователя по задачам этого курса
            # Только те, что сделаны внутри времени олимпиады
            submissions = Submission.objects.filter(
                user=user,
                task__module__course=course
            ).select_related('task')
            
            # Фильтруем по времени олимпиады
            if course.start_time:
                submissions = submissions.filter(created_at__gte=course.start_time)
            if course.end_time:
                submissions = submissions.filter(created_at__lte=course.end_time)
            
            # Если после фильтрации по времени нет сабмитов, пропускаем пользователя
            if not submissions.exists():
                continue
            
            # Находим решённые задачи (есть хотя бы один ACCEPTED)
            solved_task_ids = set()
            last_accepted_times = {}  # время последнего ACCEPTED для каждой задачи
            
            for sub in submissions:
                if sub.status == 'accepted':
                    solved_task_ids.add(sub.task_id)
                    # Обновляем время последнего ACCEPTED для этой задачи
                    if sub.task_id not in last_accepted_times or \
                       sub.created_at > last_accepted_times[sub.task_id]:
                        last_accepted_times[sub.task_id] = sub.created_at
            
            solved_count = len(solved_task_ids)
            
            # Считаем submission_count только по решённым задачам
            submission_count = 0
            if solved_task_ids:
                submission_count = submissions.filter(
                    task_id__in=solved_task_ids
                ).count()
            
            # Время последнего ACCEPTED среди всех решённых задач
            last_accepted_at = None
            if last_accepted_times:
                last_accepted_at = max(last_accepted_times.values())
            
            leaderboard_data.append({
                'user_id': user.id,
                'username': user.username,
                'solved_count': solved_count,
                'submission_count': submission_count,
                'last_accepted_at': last_accepted_at
            })
        
        # Сортировка:
        # 1. Больше solved_count - выше
        # 2. При равенстве - меньше submission_count - выше
        # 3. При равенстве - раньше last_accepted_at - выше
        # Если last_accepted_at None, ставим в конец (далекое будущее)
        leaderboard_data.sort(
            key=lambda x: (
                -x['solved_count'],  # больше = выше (отрицание для сортировки по убыванию)
                x['submission_count'],  # меньше = выше
                x['last_accepted_at'] if x['last_accepted_at'] else timezone.now() + timedelta(days=365)  # раньше = выше, None = в конец
            )
        )
        
        # Добавляем ранги
        for idx, entry in enumerate(leaderboard_data, start=1):
            entry['rank'] = idx
        
        return Response({
            'course': {
                'id': course.id,
                'title': course.title,
                'is_olimpiad': course.is_olimpiad,
                'start_time': course.start_time,
                'end_time': course.end_time,
                'is_finished': course.is_olimpiad_finished
            },
            'leaderboard': leaderboard_data
        })
