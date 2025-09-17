from django.urls import path
from .views import RegisterView, VerifyCodeView, LoginView, LogoutView,ProfileView

urlpatterns = [
    # Регистрация: отправка кода
    path('register/', RegisterView.as_view(), name='register'),

    # Подтверждение кода и создание пользователя
    path('verify/', VerifyCodeView.as_view(), name='verify'),

    # Login → выдаёт JWT
    path('login/', LoginView.as_view(), name='login'),

    # Profile 
    path('profile/', ProfileView.as_view(), name='profile'),

    # Logout → просто для завершения сессии (JWT удаляется на клиенте)
    path('logout/', LogoutView.as_view(), name='logout'),
]
