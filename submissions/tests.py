from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch
from django.utils import timezone
from courses.models import Course, Module, Task, Enrollment
from submissions.models import Submission


class DummyResponse:
    def __init__(self, text):
        self.text = text


class SubmitCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="ownerpass")
        self.user = User.objects.create_user(username="student", email="student@example.com", password="studentpass")

        self.course = Course.objects.create(
            title="Course 1",
            description="Desc",
            start_time=timezone.now(),
            owner=self.owner,
        )
        self.module = Module.objects.create(course=self.course, title="Module 1", description="", order=1)
        self.task = Task.objects.create(module=self.module, title="Task 1", description="Check print", task_text="Напишите программу, печатающую Hello", order=1)

        # JWT авторизация
        token_resp = self.client.post("/api/token/", {"username": "student", "password": "studentpass"}, format="json")
        self.assertEqual(token_resp.status_code, 200)
        access = token_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    @patch("submissions.views.model.generate_content", return_value=DummyResponse('{"status":"accepted","feedback":"ok"}'))
    def test_submit_code_success(self, _mock_ai):
        Enrollment.objects.create(user=self.user, course=self.course)
        resp = self.client.post("/api/submissions/submit-code/", {"task_id": self.task.id, "code": "print('Hello')", "lang": "python"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("submission_id", resp.data)
        sub = Submission.objects.get(id=resp.data["submission_id"])
        self.assertEqual(sub.status, "accepted")

    @patch("submissions.views.model.generate_content", return_value=DummyResponse('{"status":"accepted","feedback":"ok"}'))
    def test_submit_code_requires_enrollment(self, _mock_ai):
        resp = self.client.post("/api/submissions/submit-code/", {"task_id": self.task.id, "code": "print('Hello')", "lang": "python"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_lang(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        resp = self.client.post("/api/submissions/submit-code/", {"task_id": self.task.id, "code": "print('Hello')", "lang": "pascal"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_code_too_long(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        long_code = "a" * 10001
        resp = self.client.post("/api/submissions/submit-code/", {"task_id": self.task.id, "code": long_code, "lang": "python"}, format="json")
        self.assertEqual(resp.status_code, 400)

# Create your tests here.
