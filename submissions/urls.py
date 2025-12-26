from django.urls import path
from .views import submit_code,run_code

urlpatterns = [
    path('submit-code/', submit_code, name='submit-code'),
    path('run-code/', run_code, name='run-code'),
]