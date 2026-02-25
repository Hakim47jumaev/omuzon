from django.urls import path
from . import views

app_name = 'customadmin'

urlpatterns = [
    path('', views.CourseListView.as_view(), name='home'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_update'),
    path('courses/<int:pk>/enrollments/', views.CourseEnrollmentsView.as_view(), name='course_enrollments'),
    path('courses/<int:course_pk>/modules/add/', views.ModuleCreateView.as_view(), name='module_create'),
    path('modules/<int:pk>/', views.ModuleDetailView.as_view(), name='module_detail'),
    path('modules/<int:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_update'),
    path('modules/<int:module_pk>/tasks/add/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('login/', views.DashboardLoginView.as_view(), name='login'),
    path('logout/', views.DashboardLogoutView.as_view(), name='logout'),
]
