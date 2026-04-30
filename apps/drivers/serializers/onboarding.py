from rest_framework import serializers
from ..models import DriverOnboardingRequest
from apps.accounts.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

User = get_user_model()

class DriverOnboardingQuestionnaireSerializer(serializers.ModelSerializer):
    """Serializer for driver onboarding questionnaire (Step 1)"""
    
    # Basic Information
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    home_postcode = serializers.CharField(max_length=255, required=True)
    
    # JSON fields that need special handling
    previous_companies = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    familiar_areas = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    preferred_journey_types = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    preferred_locations = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    
    class Meta:
        model = DriverOnboardingRequest
        fields = [
            # Basic Information
            'full_name', 'mobile_number', 'email_address', 'home_postcode', 
            'preferred_communication', 'username', 'password', 'confirm_password', 'location',
            
            # Driving Experience
            'years_experience', 'previous_companies', 'familiar_areas', 
            'preferred_journey_types',
            
            # Vehicle Information
            'vehicle_ownership', 'vehicle_type', 'fuel_type',
            
            # Preferences & Availability
            'preferred_locations', 'availability', 'notification_method',
            
            # Compliance & Safety
            'has_tfl_licence', 'willing_dbs_check', 'agrees_policies',
        ]
    
    def validate(self, data):
        # Validate password confirmation
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Ensure JSON fields are properly formatted
        if 'previous_companies' in data and not isinstance(data['previous_companies'], list):
            data['previous_companies'] = []
        if 'familiar_areas' in data and not isinstance(data['familiar_areas'], list):
            data['familiar_areas'] = []
        if 'preferred_journey_types' in data and not isinstance(data['preferred_journey_types'], list):
            data['preferred_journey_types'] = []
        if 'preferred_locations' in data and not isinstance(data['preferred_locations'], list):
            data['preferred_locations'] = []
        
        return data
    
    def validate_agrees_policies(self, value):
        # Optional: Add conditional validation
        # if not value:
        #     raise serializers.ValidationError("You must agree to the policies to continue.")
        return value
    
    def validate_willing_dbs_check(self, value):
        # Optional: Add conditional validation  
        # if not value:
        #     raise serializers.ValidationError("You must be willing to undergo DBS checks to continue.")
        return value
    
    def validate_mobile_number(self, value):
        """Validate mobile number with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Mobile number is required."),
                "رقم الهاتف المحمول مطلوب."
            ])
        
        if len(value) < 10:
            raise serializers.ValidationError([
                _("Mobile number is too short. Please use international format (e.g., +447700900123)."),
                "رقم الهاتف قصير جداً. يرجى استخدام التنسيق الدولي (مثل: +447700900123)."
            ])
        
        if not value.startswith('+'):
            raise serializers.ValidationError([
                _("Mobile number must start with country code (e.g., +44 for UK, +1 for US)."),
                "رقم الهاتف يجب أن يبدأ برمز الدولة (مثل: +44 للمملكة المتحدة، +1 للولايات المتحدة)."
            ])
        
        return value
    
    def validate_email_address(self, value):
        """Validate email address with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Email address is required."),
                "عنوان البريد الإلكتروني مطلوب."
            ])
        
        if '@' not in value or '.' not in value:
            raise serializers.ValidationError([
                _("Please enter a valid email address (e.g., john@example.com)."),
                "يرجى إدخال عنوان بريد إلكتروني صحيح (مثل: john@example.com)."
            ])
        
        return value
    
    def validate_full_name(self, value):
        """Validate full name with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Full name is required."),
                "الاسم الكامل مطلوب."
            ])
        
        value = value.strip()
        
        if len(value) < 2:
            raise serializers.ValidationError([
                _("Full name must be at least 2 characters long."),
                "الاسم الكامل يجب أن يكون على الأقل حرفين."
            ])
        
        # Check if full name contains at least first name and last name (2 words minimum)
        name_parts = value.split()
        if len(name_parts) < 2:
            raise serializers.ValidationError([
                _("Full name must include both first name and last name (e.g., 'John Doe')."),
                "الاسم الكامل يجب أن يتضمن الاسم الأول واسم العائلة (مثال: 'أحمد محمد')."
            ])
        
        return value
    
    def validate_username(self, value):
        """Validate username with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Username is required."),
                "اسم المستخدم مطلوب."
            ])
        
        if len(value) < 3:
            raise serializers.ValidationError([
                _("Username must be at least 3 characters long."),
                "اسم المستخدم يجب أن يكون على الأقل 3 أحرف."
            ])
        
        return value
    
    def validate_password(self, value):
        """Validate password with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Password is required."),
                "كلمة المرور مطلوبة."
            ])
        
        if len(value) < 8:
            raise serializers.ValidationError([
                _("Password must be at least 8 characters long."),
                "كلمة المرور يجب أن تكون على الأقل 8 أحرف."
            ])
        
        return value
    
    def validate_confirm_password(self, value):
        """Validate confirm password with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Password confirmation is required."),
                "تأكيد كلمة المرور مطلوب."
            ])
        
        return value
    
    def validate_home_postcode(self, value):
        """Validate home postcode with bilingual error messages"""
        if not value or not value.strip():
            raise serializers.ValidationError([
                _("Home postcode is required."),
                "الرمز البريدي للمنزل مطلوب."
            ])
        
        if len(value) > 255:
            raise serializers.ValidationError([
                _("Home postcode is too long (maximum 255 characters)."),
                "الرمز البريدي للمنزل طويل جداً (الحد الأقصى 255 حرف)."
            ])
        
        return value.strip()
    
    def validate_familiar_areas(self, value):
        """Validate familiar areas with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Familiar areas are required."),
                "المناطق المألوفة مطلوبة."
            ])
        
        if not isinstance(value, list):
            raise serializers.ValidationError([
                _("Familiar areas must be a list of areas."),
                "المناطق المألوفة يجب أن تكون قائمة بالمناطق."
            ])
        
        if len(value) == 0:
            raise serializers.ValidationError([
                _("Please specify at least one familiar area."),
                "يرجى تحديد منطقة مألوفة واحدة على الأقل."
            ])
        
        return value
    
    def validate_preferred_locations(self, value):
        """Validate preferred locations with bilingual error messages"""
        if not value:
            raise serializers.ValidationError([
                _("Preferred locations are required."),
                "المواقع المفضلة مطلوبة."
            ])
        
        if not isinstance(value, list):
            raise serializers.ValidationError([
                _("Preferred locations must be a list of locations."),
                "المواقع المفضلة يجب أن تكون قائمة بالمواقع."
            ])
        
        if len(value) == 0:
            raise serializers.ValidationError([
                _("Please specify at least one preferred location."),
                "يرجى تحديد موقع مفضل واحد على الأقل."
            ])
        
        return value
    
    def create(self, validated_data):
        # Extract user data but don't create user yet
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        confirm_password = validated_data.pop('confirm_password')
        # Remove location field if present (it's optional and not stored in model)
        validated_data.pop('location', None)
        
        # Store user data for later creation
        user_data = {
            'username': username,
            'email': validated_data['email_address'],
            'password': password,
            'confirm_password': confirm_password,
            'first_name': validated_data['full_name'].split()[0] if validated_data['full_name'] else '',
            'last_name': ' '.join(validated_data['full_name'].split()[1:]) if len(validated_data['full_name'].split()) > 1 else '',
            'phone_number': validated_data['mobile_number'],
            'address': validated_data['home_postcode'],
            'account_type': 'normal_driver',
            'is_active': False,  # Will be activated after step 1 approval
            'is_profile_completed': False,
            'is_admin_verified': False,
        }
        
        # Create a temporary user for the onboarding request
        # This user will be inactive until step 1 is approved
        user_serializer = CustomUserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        # Create onboarding request
        validated_data['user'] = user
        onboarding_request = super().create(validated_data)
        
        return onboarding_request

class DriverOnboardingRequestSerializer(serializers.ModelSerializer):
    """Serializer for admin review of onboarding requests"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    # JSON fields that need special handling
    previous_companies = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    familiar_areas = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    preferred_journey_types = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    preferred_locations = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    files_need_modification = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    
    class Meta:
        model = DriverOnboardingRequest
        fields = [
            'id', 'full_name', 'mobile_number', 'email_address', 'home_postcode',
            'preferred_communication', 'years_experience', 'previous_companies',
            'familiar_areas', 'preferred_journey_types', 'vehicle_ownership',
            'vehicle_type', 'fuel_type', 'preferred_locations', 'availability',
            'notification_method', 'has_tfl_licence', 'willing_dbs_check',
            'agrees_policies', 'status', 'admin_notes', 'rejection_reason',
            'reviewed_by', 'reviewed_at', 'created_at', 'user_email', 'user_username',
            'files_need_modification', 'modification_confirmed'
        ]
        read_only_fields = ['id', 'created_at', 'reviewed_by', 'reviewed_at']

class DriverOnboardingApprovalSerializer(serializers.Serializer):
    """Serializer for admin approval/rejection/modification actions"""
    
    action = serializers.ChoiceField(choices=['approve', 'reject', 'modify'])
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    files_to_modify = serializers.ListField(
        child=serializers.ChoiceField(choices=['pco', 'dbs', 'dvla', 'mot', 'phv']),
        required=False,
        allow_empty=True,
        help_text="List of file names that need modification"
    )
    
    def validate(self, data):
        action = data.get('action')
        rejection_reason = data.get('rejection_reason', '')
        files_to_modify = data.get('files_to_modify', [])
        
        if action in ['reject', 'modify'] and not rejection_reason:
            from django.utils.translation import gettext as _
            raise serializers.ValidationError({
                'rejection_reason': _('Reason is required when rejecting or requesting modification.')
            })
        
        if action == 'modify':
            if not files_to_modify:
                from django.utils.translation import gettext as _
                raise serializers.ValidationError({
                    'files_to_modify': _('At least one file must be selected for modification.')
                })
        
        return data
