# courses/urls.py
from django.urls import path
from .views import (
    CourseListView,
    CourseDetailView,
    MyEnrolledCoursesView,
    ModuleDetailView,
    TaskDetailView,
    EnrollView,
    CourseCreateView,
    CourseUpdateView,
    CourseDeleteView,
)

urlpatterns = [
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('courses/enrolled/', MyEnrolledCoursesView.as_view(), name='my-courses'),
    path('courses/enroll/', EnrollView.as_view(), name='enroll'),

    path('modules/<int:pk>/', ModuleDetailView.as_view(), name='module-detail'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),

    path('courses/create/', CourseCreateView.as_view(), name='course-create'),
    path('courses/<int:pk>/update/', CourseUpdateView.as_view(), name='course-update'),
    path('courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='course-delete'),
]