# accounts/urls.py
from django.urls import path
from .views import (
    RegisterView, VerifyCodeView, LoginView,
    LogoutView, ProfileView, ResendCodeView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyCodeView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
]