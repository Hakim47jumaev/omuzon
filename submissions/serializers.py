from rest_framework import serializers
from .models import Submission

class SubmissionSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(write_only=True)
    code = serializers.CharField()
    lang = serializers.CharField(default="python", required=False)

    class Meta:
        model = Submission
        fields = ['task_id', 'code','lang']