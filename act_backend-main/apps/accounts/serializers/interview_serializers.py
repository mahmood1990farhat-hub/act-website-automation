from rest_framework import serializers
from ..models import Interview
from django.utils import timezone
from django.utils.translation import gettext as _ 

class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ['interview_date', 'interview_time', 'status']
        read_only_fields = ["id", "status"]
    
    def validate_interview_date(self, value):
        today = timezone.localdate()
        if value <= today:
            raise serializers.ValidationError(_("Interview date must be greater than today."))
        return value