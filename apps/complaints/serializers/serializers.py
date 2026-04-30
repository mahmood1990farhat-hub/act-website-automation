from rest_framework import serializers
from ..models import Complaint, TripComplaint, LostProperty
from apps.trips.models import Trip
import base64
import uuid
from django.core.files.base import ContentFile

class ComplaintSerializer(serializers.ModelSerializer):
    complainant = serializers.SerializerMethodField()
    class Meta:
        model = Complaint
        fields = ['id', 'title', 'description', 'resolved', 'created_at' , 'complainant']
        read_only_fields = ['id', 'resolved', 'created_at']
        
    def get_complainant(self , obj):
        user = obj.user
        return {
            'full_name': f"{user.first_name} {user.last_name}",
            'phone_number': user.phone_number,
            'account_type': user.account_type
        }


class TripNestedSerializer(serializers.ModelSerializer):
    passenger_info = serializers.SerializerMethodField()
    driver_info = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id',
            'expected_trip_duration_minutes',
            'distance_miles',
            'trip_date',
            'trip_time',
            'route_polyline',
            'passenger_info',
            'driver_info'
        ]

    def get_passenger_info(self, obj):
        if not obj.passenger or not obj.passenger.user:
            return None
        user = obj.passenger.user
        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number
        }

    def get_driver_info(self, obj):
        if not obj.base_driver or not obj.base_driver.user:
            return None
        user = obj.base_driver.user
        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number
        }


class TripComplaintSerializer(serializers.ModelSerializer):
    trip_data = TripNestedSerializer(source='trip', read_only=True)
    complainant = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)

    class Meta:
        model = TripComplaint
        fields = [
            'id', 'user', 'trip', 'complaint_type', 'complaint_type_display', 
            'title', 'description', 'status', 'status_display', 'admin_response',
            'resolved_at', 'created_at', 'trip_data', 'complainant', 'resolved'
        ]
        read_only_fields = [
            'id', 'created_at', 'user', 'resolved', 'status', 
            'admin_response', 'resolved_at'
        ]
    
    def validate(self, attrs):
        trip = attrs.get('trip')
        user = self.context['request'].user
        complaint_type = attrs.get('complaint_type')

        valid_types = ['trip_issue', 'driver_issue', 'service_issue', 'payment_issue', 'other']
        if complaint_type and complaint_type not in valid_types:
            raise serializers.ValidationError("Invalid complaint type.")

        if trip:
            # Only passengers can submit complaints about their trips
            if not hasattr(user, 'passenger_profile'):
                raise serializers.ValidationError("Only passengers can submit trip complaints.")
            if trip.passenger.user_id != user.id:
                raise serializers.ValidationError("This trip does not belong to you.")
            if trip.status != 'completed':
                raise serializers.ValidationError("You can only complain about completed trips.")
        
        return attrs

    def get_complainant(self, obj):
        user = obj.user
        return {
            'full_name': f"{user.first_name} {user.last_name}",
            'phone_number': user.phone_number,
            'email': user.email,
            'account_type': user.account_type
        }


class LostPropertySerializer(serializers.ModelSerializer):
    trip_data = TripNestedSerializer(source='trip', read_only=True)
    reporter = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    contact_preference_display = serializers.CharField(source='get_contact_preference_display', read_only=True)
    photo_base64 = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True, help_text="Base64 encoded photo of the lost item")
    photo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LostProperty
        fields = [
            'id', 'user', 'trip', 'trip_data', 'item_type', 'item_type_display',
            'item_description', 'item_color', 'item_brand', 'lost_location',
            'contact_preference', 'contact_preference_display', 'status',
            'status_display', 'admin_notes', 'found_at', 'returned_at',
            'created_at', 'updated_at', 'reporter', 'photo', 'photo_base64'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'user', 'status',
            'admin_notes', 'found_at', 'returned_at', 'photo'
        ]
    
    def validate(self, attrs):
        trip = attrs.get('trip')
        user = self.context['request'].user

        if trip:
            # Only passengers can report lost property
            if not hasattr(user, 'passenger_profile'):
                raise serializers.ValidationError("Only passengers can report lost property.")
            if trip.passenger.user_id != user.id:
                raise serializers.ValidationError("This trip does not belong to you.")
            if trip.status != 'completed':
                raise serializers.ValidationError("You can only report lost property for completed trips.")
        
        return attrs

    def get_reporter(self, obj):
        user = obj.user
        return {
            'full_name': f"{user.first_name} {user.last_name}",
            'phone_number': user.phone_number,
            'email': user.email,
        }
    
    def get_photo(self, obj):
        """Convert photo to base64 format for API response"""
        if not obj.photo:
            return None
        
        try:
            obj.photo.open()
            file_content = obj.photo.read()
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            obj.photo.close()
            
            import os
            filename = os.path.basename(obj.photo.name) if obj.photo.name else None
            file_extension = os.path.splitext(filename)[1] if filename else None
            
            return {
                'content': file_base64,
                'filename': filename,
                'extension': file_extension,
                'size': len(file_content)
            }
        except Exception as e:
            return None
    
    def create(self, validated_data):
        """Handle base64 photo upload during creation"""
        photo_base64 = validated_data.pop('photo_base64', None)
        
        # Convert base64 to file if provided
        if photo_base64:
            photo_file = self._decode_base64_photo(photo_base64)
            if photo_file:
                validated_data['photo'] = photo_file
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Handle base64 photo upload during update"""
        photo_base64 = validated_data.pop('photo_base64', None)
        
        # Convert base64 to file if provided
        if photo_base64:
            photo_file = self._decode_base64_photo(photo_base64)
            if photo_file:
                validated_data['photo'] = photo_file
        
        return super().update(instance, validated_data)
    
    def _decode_base64_photo(self, base64_string):
        """Decode base64 string to Django file object"""
        if not base64_string or not base64_string.strip():
            return None
        
        try:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            decoded_file = base64.b64decode(base64_string)
            
            # Determine file extension from decoded content
            # Check magic bytes to detect image type
            file_extension = '.jpg'  # default
            if len(decoded_file) >= 4:
                # Check for PNG signature
                if decoded_file[:4] == b'\x89PNG':
                    file_extension = '.png'
                # Check for JPEG signature
                elif decoded_file[:2] == b'\xff\xd8':
                    file_extension = '.jpg'
                # Check for GIF signature
                elif decoded_file[:3] == b'GIF':
                    file_extension = '.gif'
                # Check for WebP signature
                elif decoded_file[:4] == b'RIFF' and decoded_file[8:12] == b'WEBP':
                    file_extension = '.webp'
            
            # Generate unique filename
            filename = f"lost_property_{uuid.uuid4().hex[:12]}{file_extension}"
            
            # Create Django file object
            file_content = ContentFile(decoded_file, name=filename)
            
            return file_content
        except Exception as e:
            raise serializers.ValidationError({
                'photo_base64': f'Invalid base64 image data: {str(e)}'
            })
