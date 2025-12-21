# accounts/urls.py
from django.urls import path
from .views import (
    RegisterView, VerifyCodeView, LoginView,
    LogoutView, ProfileView, ResendCodeView,ProfileEducationView
)
from .api.google_signin import GoogleSignInAPIView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyCodeView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('google-signin/', GoogleSignInAPIView.as_view(), name='google-signin'),
    path('profile/education/', ProfileEducationView.as_view()),
]