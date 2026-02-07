from django.urls import path
from . import views

app_name = 'customadmin'

urlpatterns = [
    path('login/', views.DashboardLoginView.as_view(), name='login'),
    path('logout/', views.DashboardLogoutView.as_view(), name='logout'),
    
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_update'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    
    path('modules/', views.ModuleListView.as_view(), name='module_list'),
    path('modules/add/', views.ModuleCreateView.as_view(), name='module_create'),
    path('modules/<int:pk>/', views.ModuleDetailView.as_view(), name='module_detail'),
    path('modules/<int:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_update'),
    path('modules/<int:pk>/delete/', views.ModuleDeleteView.as_view(), name='module_delete'),
    
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/add/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    
    path('testcases/', views.TestCaseListView.as_view(), name='testcase_list'),
    path('testcases/add/', views.TestCaseCreateView.as_view(), name='testcase_create'),
    path('testcases/<int:pk>/edit/', views.TestCaseUpdateView.as_view(), name='testcase_update'),
    path('testcases/<int:pk>/delete/', views.TestCaseDeleteView.as_view(), name='testcase_delete'),
]
