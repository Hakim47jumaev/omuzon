from django.urls import path
from .views import submit_code, run_code, get_submission

urlpatterns = [
    path('submit-code/', submit_code, name='submit-code'),
    path('run-code/', run_code, name='run-code'),
    path('<int:submission_id>/', get_submission, name='get-submission'),
]