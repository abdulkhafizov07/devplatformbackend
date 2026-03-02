from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('profile_image', 'bio', 'phone', 'address')
        extra_kwargs = {
            'profile_image': {'required': False}
        }

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'profile')
        extra_kwargs = {
            'email': {'required': False}
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update User fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        
        # Update Profile fields
        if profile_data:
            profile = instance.profile
            profile.profile_image = profile_data.get('profile_image', profile.profile_image)
            profile.bio = profile_data.get('bio', profile.bio)
            profile.phone = profile_data.get('phone', profile.phone)
            profile.address = profile_data.get('address', profile.address)
            profile.save()
        
        return instance
        