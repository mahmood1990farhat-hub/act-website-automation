from rest_framework import serializers
from ..models import StopPoint
from django.utils.translation import gettext as _

class StopPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopPoint
        fields = ['point_lat' , 'point_lng' ,'point_place_id' , 'point_postal_code'  ,'point_str']

