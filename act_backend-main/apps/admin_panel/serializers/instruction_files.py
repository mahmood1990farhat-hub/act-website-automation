from rest_framework import serializers
from apps.admin_panel.models.instruction_files import InstructionFile


class InstructionFileSerializer(serializers.ModelSerializer):
    """Serializer for instruction files"""
    language = serializers.ChoiceField(choices=InstructionFile.LANGUAGE_CHOICES, required=True)
    file_url = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    updated_by_email = serializers.CharField(source='updated_by.email', read_only=True)
    
    class Meta:
        model = InstructionFile
        fields = [
            'id',
            'file_type',
            'language',
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
    
    def validate(self, attrs):
        language = attrs.get('language', getattr(self.instance, 'language', ''))
        if not language:
            raise serializers.ValidationError({'language': 'Confirm the actual document language before saving.'})
        file_type = attrs.get('file_type', getattr(self.instance, 'file_type', None))
        duplicates = InstructionFile.objects.filter(file_type=file_type, language=language)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({'language': 'A document of this type already exists in this language. Edit that version instead.'})
        return attrs

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
            'language',
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
