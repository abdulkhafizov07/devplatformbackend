# courses/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Course, Episode, Review, Enrollment ,SavedCourse

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'order']

class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = [
            'id', 'title', 'slug', 'description', 'iframe', 'duration',
            'order', 'is_free', 'is_active', 'attachment', 'created_at'
        ]

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'user', 'rating', 'comment', 'is_approved',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'is_approved']

class CourseListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    instructor = serializers.StringRelatedField()
    is_discounted = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'short_description', 'thumbnail',
            'categories', 'instructor', 'level', 'duration',
            'price', 'discount_price', 'current_price', 'is_discounted',
            'is_free', 'is_featured', 'total_lessons', 'total_duration',
            'average_rating', 'total_reviews', 'total_students',
            'status', 'created_at'
        ]

class CourseDetailSerializer(CourseListSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    description = serializers.CharField()
    
    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            'description', 'iframe', 'episodes', 'reviews'
        ]

class CourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'short_description', 'thumbnail',
            'categories', 'level', 'duration', 'price', 'discount_price',
            'is_featured', 'is_free', 'status', 'iframe'
        ]

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    completed_episodes = EpisodeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'course', 'progress', 'is_completed', 'is_active',
            'enrolled_at', 'completed_at', 'completed_episodes'
        ]


class SavedCourseSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = SavedCourse
        fields = ['id', 'user', 'course', 'saved_at']
        read_only_fields = ['user', 'saved_at']


class SavedCourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCourse
        fields = ['course']   # faqat kurs ID si yuboriladi