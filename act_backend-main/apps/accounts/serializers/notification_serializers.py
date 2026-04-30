from rest_framework import serializers
from ..models import Notification
from django.utils.translation import gettext as _

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    Returns bilingual content based on user's locale preference.
    """
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'title_en', 'title_ar', 'desc_en', 'desc_ar', 
                  'mobile_url', 'web_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_title(self, obj):
        """Get title based on request locale"""
        request = self.context.get('request')
        if request:
            locale = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            if 'ar' in locale.lower():
                return obj.title_ar
        return obj.title_en
    
    def get_message(self, obj):
        """Get message/description based on request locale"""
        request = self.context.get('request')
        if request:
            locale = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            if 'ar' in locale.lower():
                return obj.desc_ar
        return obj.desc_en
