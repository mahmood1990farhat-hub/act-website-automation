from rest_framework import serializers
from apps.admin_panel.models.instruction_files import InstructionFile


class InstructionFileSerializer(serializers.ModelSerializer):
    """Serializer for instruction files"""
    file_url = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    updated_by_email = serializers.CharField(source='updated_by.email', read_only=True)
    
    class Meta:
        model = InstructionFile
        fields = [
            'id',
            'file_type',
            'file_type_display',
            'title',
            'file',
            'file_url',
            'description',
            'is_active',
            'version',
            'created_by',
            'created_by_email',
            'updated_by',
            'updated_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'file_url', 'version', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        """Get full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class InstructionFilePublicSerializer(serializers.ModelSerializer):
    """Public serializer for instruction files (no admin info)"""
    file_url = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    
    class Meta:
        model = InstructionFile
        fields = [
            'id',
            'file_type',
            'file_type_display',
            'title',
            'file_url',
            'description',
            'version',
            'updated_at',
        ]
        read_only_fields = fields
    
    def get_file_url(self, obj):
        """Get full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
