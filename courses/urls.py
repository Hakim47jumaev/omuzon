from django.urls import path
from . import views

urlpatterns = [
    # ----------------- Courses -----------------
    path('courses/', views.CourseListView.as_view(), name='course-list'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course-create'),
    path('courses/<int:pk>/update/', views.CourseUpdateView.as_view(), name='course-update'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course-delete'),

    # ----------------- Modules -----------------
    path('modules/<int:pk>/', views.ModuleDetailView.as_view(), name='module-detail'),
    path('modules/create/', views.ModuleCreateView.as_view(), name='module-create'),
    path('modules/<int:pk>/update/', views.ModuleUpdateView.as_view(), name='module-update'),
    path('modules/<int:pk>/delete/', views.ModuleDeleteView.as_view(), name='module-delete'),

    # ----------------- Tasks -----------------
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task-update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task-delete'),

    # ----------------- Enrollment -----------------
    path('enroll/', views.EnrollView.as_view(), name='enroll'),

    # ----------------- User Courses -----------------
    path('my-courses/', views.MyEnrolledCoursesView.as_view(), name='my-enrolled-courses'),
]
