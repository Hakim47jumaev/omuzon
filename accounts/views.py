# accounts/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    RegisterSerializer, VerifyCodeSerializer,
    LoginSerializer, UserSerializer, ProfileSerializer
)
from .models import EmailVerification


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Verification code sent to your email."})

 
class VerifyCodeView(generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()  # ← пользователь создан

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Account created successfully.",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user.profile


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out."})


# РЕСЕНД КОДА
class ResendCodeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            ev = EmailVerification.objects.get(email=email, is_used=False)
            ev.verification_code = EmailVerification.generate_code()
            ev.created_at = timezone.now()
            ev.save()
            ev.send_code()
            return Response({"message": "New verification code sent."})
        except EmailVerification.DoesNotExist:
            return Response({"error": "No pending registration for this email."}, status=400)
        


 
from rest_framework.permissions import IsAuthenticated
 
from courses.models import Enrollment
from submissions.models import Submission
from .serializers import ProfileEducationSerializer


class ProfileEducationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        enrollments = (
            Enrollment.objects
            .filter(user=user)
            .select_related('course')
            .prefetch_related('course__modules__tasks')
        )

        submissions = (
            Submission.objects
            .filter(user=user)
            .select_related('task', 'task__module')
            .order_by('created_at')
        )

        submissions_by_task = {}
        for s in submissions:
            submissions_by_task.setdefault(s.task_id, []).append(s)

        courses_data = []

        completed_courses = 0
        in_progress_courses = 0
        total_solved_tasks = 0

        for enrollment in enrollments:
            course = enrollment.course

            task_ids = []
            for m in course.modules.all():
                for t in m.tasks.all():
                    task_ids.append(t.id)

            total_tasks = len(task_ids)
            solved_tasks = 0

            for task_id in task_ids:
                subs = submissions_by_task.get(task_id, [])
                if any(s.status == 'accepted' for s in subs):
                    solved_tasks += 1

            progress = round((solved_tasks / total_tasks) * 100, 1) if total_tasks else 0

            if course.start_time > timezone.now():
                status = 'not_started'
            elif progress == 100:
                status = 'completed'
                completed_courses += 1
            elif progress > 0:
                status = 'in_progress'
                in_progress_courses += 1
            else:
                status = 'in_progress'
                in_progress_courses += 1

            total_solved_tasks += solved_tasks

            courses_data.append({
                'course_id': course.id,
                'title': course.title,
                'start_time': course.start_time,
                'is_active': course.start_time <= timezone.now(),
                'status': status,
                'progress_percent': progress,
                'solved_tasks': solved_tasks,
                'total_tasks': total_tasks
            })

        summary = {
            'enrolled_courses': enrollments.count(),
            'completed_courses': completed_courses,
            'in_progress_courses': in_progress_courses,
            'total_solved_tasks': total_solved_tasks,
            'total_submissions': submissions.count()
        }

        serializer = ProfileEducationSerializer({
            'summary': summary,
            'courses': courses_data
        })

        return Response(serializer.data)
