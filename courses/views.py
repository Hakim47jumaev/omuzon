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

from datetime import timedelta
from django.db.models import (
    Q, F, Value, IntegerField,
    Count, Max, Sum, Case, When
)
from django.db.models.functions import Coalesce
from django.db.models.expressions import OrderBy
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status


class OlimpiadLeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Курс не найден"}, status=status.HTTP_404_NOT_FOUND)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        now = timezone.now()

        # --- cutoff_time (для олимпиады делаем freeze-snapshot) ---
        cutoff_time = now

        if course.is_olimpiad and course.end_time:
            freeze_point = course.end_time - timedelta(minutes=30)

            if now >= course.end_time:
                # финальные результаты
                cutoff_time = course.end_time
            elif now >= freeze_point:
                # последние 30 минут -> snapshot на момент freeze_point
                cutoff_time = freeze_point
            else:
                # до freeze зоны -> актуально на сейчас
                cutoff_time = now

        # --- фильтр сабмитов ---
        sub_filter = Q(task__module__course=course)

        # если олимпиада — обязательно в окне времени
        if course.is_olimpiad:
            sub_filter &= Q(created_at__gte=course.start_time)
            sub_filter &= Q(created_at__lte=cutoff_time)
        else:
            # обычный курс: можно считать за всё время
            # (если хочешь ограничить с момента старта курса — добавь created_at__gte=course.start_time)
            sub_filter &= Q(created_at__lte=now)

        task_stats = (
            Submission.objects
            .filter(sub_filter)
            .values("user_id", "task_id")
            .annotate(
                attempts=Count("id"),
                is_solved=Max(Case(
                    When(status="accepted", then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )),
                accepted_time=Max(Case(
                    When(status="accepted", then=F("created_at")),
                    default=None,
                )),
            )
        )

        user_stats = (
            task_stats
            .values("user_id")
            .annotate(
                solved_count=Coalesce(Sum("is_solved"), Value(0)),
                submission_count=Coalesce(
                    Sum(Case(
                        When(is_solved=1, then=F("attempts")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )),
                    Value(0),
                ),
                last_accepted_at=Max("accepted_time"),
            )
        )

        user_ids = [row["user_id"] for row in user_stats]
        users_map = User.objects.in_bulk(user_ids)

        try:
            ordered_rows = list(user_stats.order_by(
                F("solved_count").desc(),
                F("submission_count").asc(),
                OrderBy(F("last_accepted_at"), ascending=True, nulls_last=True),
            ))
        except Exception:
            ordered_rows = list(user_stats)
            far_future = now + timedelta(days=365)
            ordered_rows.sort(key=lambda x: (
                -int(x["solved_count"] or 0),
                int(x["submission_count"] or 0),
                x["last_accepted_at"] if x["last_accepted_at"] else far_future
            ))

        leaderboard = []
        for idx, row in enumerate(ordered_rows, start=1):
            u = users_map.get(row["user_id"])
            if not u:
                continue
            leaderboard.append({
                "rank": idx,
                "user_id": row["user_id"],
                "username": u.username,
                "solved_count": int(row["solved_count"] or 0),
                "submission_count": int(row["submission_count"] or 0),
                "last_accepted_at": row["last_accepted_at"],
            })

        return Response({
            "course": {
                "id": course.id,
                "title": course.title,
                "is_olimpiad": course.is_olimpiad,
                "start_time": course.start_time,
                "end_time": course.end_time,
                "is_finished": course.is_olimpiad_finished,
            },
            "leaderboard": leaderboard
        }, status=status.HTTP_200_OK)
