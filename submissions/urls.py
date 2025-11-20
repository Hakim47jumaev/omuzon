from django.urls import path
from .views import submit_code

urlpatterns = [
    path('submit-code/', submit_code, name='submit-code'),
]