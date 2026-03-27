# courses/serializers.py
from rest_framework import serializers
from .models import Course, Module, Task, Enrollment,TestCase
from submissions.models import Submission
from django.utils import timezone



class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'input_data', 'expected_output', 'is_active', 'order']

# ===================== ЛЁГКИЙ СЕРИАЛИЗАТОР ДЛЯ СПИСКОВ =====================
class LightCourseSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.IntegerField(read_only=True)
    is_active = serializers.ReadOnlyField()
    is_olimpiad_active = serializers.ReadOnlyField()
    is_olimpiad_finished = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'show',
            'start_time',
            'end_time',
            'is_active',
            'is_olimpiad',
            'is_olimpiad_active',
            'is_olimpiad_finished',
            'enrolled_count'
        ]


# ===================== ЗАДАЧА =====================
class TaskSerializer(serializers.ModelSerializer):
    is_solved = serializers.SerializerMethodField()
    last_submission = serializers.SerializerMethodField()
    my_submissions = serializers.SerializerMethodField()
    testcases = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'task_text', 'order', 'is_solved','testcases' ,'last_submission', 'my_submissions']


    def get_testcases(self, obj):
        n = int(obj.show_count or 0)

        qs = obj.testcases.filter(is_active=True).order_by('order')

        if n <= 0:
            return []

        qs = qs[:n]
        return TestCaseSerializer(qs, many=True).data

    def get_is_solved(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        
        course = obj.module.course
        submissions_map = self.context.get('user_submissions_by_task')
        
        if submissions_map is not None:
            subs = submissions_map.get(obj.id, [])
            # Для олимпиадного режима проверяем время
            if course.is_olimpiad:
                now = timezone.now()
                for s in subs:
                    if s.status == 'accepted':
                        # Проверяем, что сабмит был сделан внутри времени олимпиады
                        if course.start_time and s.created_at < course.start_time:
                            continue
                        if course.end_time and s.created_at > course.end_time:
                            continue
                        return True
                return False
            else:
                return any(s.status == 'accepted' for s in subs)
        
        # Если submissions_map не передан, делаем запрос к БД
        queryset = Submission.objects.filter(user=user, task=obj, status='accepted')
        if course.is_olimpiad:
            if course.start_time:
                queryset = queryset.filter(created_at__gte=course.start_time)
            if course.end_time:
                queryset = queryset.filter(created_at__lte=course.end_time)
        return queryset.exists()

    def get_last_submission(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return None
        submissions_map = self.context.get('user_submissions_by_task')
        if submissions_map is not None:
            subs = submissions_map.get(obj.id, [])
            if not subs:
                return None
            last = subs[-1]
        else:
            last = (
                Submission.objects.filter(user=user, task=obj)
                .order_by('created_at')
                .last()
            )
            if last is None:
                return None
        return {
            'id': last.id,
            'status': last.status,
            'feedback': last.feedback,
            'created_at': last.created_at,
            'code': last.code,
            'lang':last.lang
        }

    def get_my_submissions(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return []
        submissions_map = self.context.get('user_submissions_by_task')
        if submissions_map is not None:
            subs = submissions_map.get(obj.id, [])
        else:
            subs = list(
                Submission.objects.filter(user=user, task=obj)
                .order_by('created_at')
            )
        return [
            {
                'id': s.id,
                'status': s.status,
                'feedback': s.feedback,
                'created_at': s.created_at,
                'code': s.code,
                'lang':s.lang
            }
            for s in subs
        ]

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
    is_olimpiad_active = serializers.ReadOnlyField()
    is_olimpiad_finished = serializers.ReadOnlyField()
    enrolled_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'show',
            'start_time',
            'end_time',
            'is_olimpiad',
            'is_olimpiad_active',
            'is_olimpiad_finished',
            'is_enrolled',
            'solved_tasks_count',
            'total_tasks',
            'progress_percent',
            'modules',
            'enrolled_count'
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
        submissions_map = self.context.get('user_submissions_by_task', {})
        accepted_task_ids = set()
        now = timezone.now()
        
        for task_id, subs in submissions_map.items():
            # Для олимпиадного режима проверяем время
            if obj.is_olimpiad:
                for s in subs:
                    if s.status == 'accepted':
                        # Проверяем, что сабмит был сделан внутри времени олимпиады
                        if obj.start_time and s.created_at < obj.start_time:
                            continue
                        if obj.end_time and s.created_at > obj.end_time:
                            continue
                        accepted_task_ids.add(task_id)
                        break
            else:
                if any(s.status == 'accepted' for s in subs):
                    accepted_task_ids.add(task_id)
        
        course_task_ids = set()
        for m in obj.modules.all():
            for t in m.tasks.all():
                course_task_ids.add(t.id)
        return len(accepted_task_ids & course_task_ids)

    def get_total_tasks(self, obj):
        total = 0
        for m in obj.modules.all():
            total += m.tasks.all().count()
        return total

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


