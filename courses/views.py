# courses/views.py
from .models import models
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import serializers
from .models import Category, Course, Episode, Review, Enrollment
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    CourseCreateSerializer, EpisodeSerializer, ReviewSerializer,
    EnrollmentSerializer,SavedCourseSerializer
)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'level', 'is_free', 'is_featured', 'status']
    search_fields = ['title', 'description', 'short_description']
    ordering_fields = ['created_at', 'price', 'average_rating', 'total_students']
    lookup_field = 'slug'
    
    def get_queryset(self):
        queryset = Course.objects.filter(status='published').order_by('-created_at')
        
        # Foydalanuvchi o'qituvchi yoki admin bo'lsa, barcha kurslarni ko'rsatish
        if self.request.user.is_authenticated:
            if self.request.user.is_staff or self.request.user.is_superuser:
                queryset = Course.objects.all().order_by('-created_at')
            elif self.action == 'my_courses':
                queryset = Course.objects.filter(
                    enrollments__user=self.request.user
                ).order_by('-enrollments__enrolled_at')
        
        # Filter by category slug
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Filter by enrollment
        enrolled = self.request.query_params.get('enrolled')
        if enrolled and self.request.user.is_authenticated:
            if enrolled == 'true':
                queryset = queryset.filter(enrollments__user=self.request.user)
            elif enrolled == 'false':
                queryset = queryset.exclude(enrollments__user=self.request.user)
        
        return queryset.distinct()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['enroll', 'mark_complete', 'my_progress']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateSerializer
        elif self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseListSerializer
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        # Ro'yxatdan o'tganligini tekshirish
        if Enrollment.objects.filter(user=user, course=course).exists():
            return Response(
                {'message': 'Siz allaqachon bu kursga yozilgansiz.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Yozilishni yaratish
        enrollment = Enrollment.objects.create(user=user, course=course)
        
        return Response(
            {
                'message': 'Kursga muvaffaqiyatli yozildingiz.',
                'data': EnrollmentSerializer(enrollment).data
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def mark_complete(self, request, slug=None):
        course = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')
        
        if not episode_id:
            return Response(
                {'message': 'Episode ID kiritilishi kerak.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            episode = Episode.objects.get(id=episode_id, course=course)
        except Episode.DoesNotExist:
            return Response(
                {'message': 'Episode topilmadi.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Yozilishni tekshirish
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        if not enrollment:
            return Response(
                {'message': 'Siz bu kursga yozilmagansiz.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Episode ni tugatilgan deb belgilash
        enrollment.completed_episodes.add(episode)
        enrollment.update_progress()
        
        return Response(
            {
                'message': 'Dars muvaffaqiyatli tugatildi.',
                'progress': enrollment.progress
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def my_progress(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        if not enrollment:
            return Response(
                {'message': 'Siz bu kursga yozilmagansiz.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(EnrollmentSerializer(enrollment).data)
    
    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        """Foydalanuvchining yozilgan kurslari"""
        enrollments = Enrollment.objects.filter(
            user=request.user, is_active=True
        ).order_by('-enrolled_at')
        
        courses = [enrollment.course for enrollment in enrollments]
        
        page = self.paginate_queryset(courses)
        if page is not None:
            serializer = CourseListSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = CourseListSerializer(
            courses, many=True, context={'request': request}
        )
        return Response(serializer.data)

class EpisodeViewSet(viewsets.ModelViewSet):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    
    def get_queryset(self):
        course_slug = self.kwargs.get('course_slug')
        course = get_object_or_404(Course, slug=course_slug, status='published')
        
        queryset = Episode.objects.filter(
            course=course, is_active=True
        ).order_by('order')
        
        # Agar foydalanuvchi kursga yozilmagan bo'lsa, faqat bepul darslarni ko'rsatish
        if self.request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(
                user=self.request.user, course=course
            ).first()
            if not enrollment:
                queryset = queryset.filter(is_free=True)
        
        return queryset

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        course_slug = self.kwargs.get('course_slug')
        course = get_object_or_404(Course, slug=course_slug, status='published')
        
        return Review.objects.filter(
            course=course, is_approved=True
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        course_slug = self.kwargs.get('course_slug')
        course = get_object_or_404(Course, slug=course_slug, status='published')
        
        # Foydalanuvchi kursga yozilganligini tekshirish
        enrollment = Enrollment.objects.filter(
            user=self.request.user, course=course
        ).first()
        
        if not enrollment:
            raise serializers.ValidationError(
                "Siz faqat yozilgan kurslarga baho qoldirishingiz mumkin."
            )
        
        serializer.save(user=self.request.user, course=course)

# ... qolgan viewsetlar (MyCoursesViewSet, DashboardViewSet, InstructorCoursesViewSet, InstructorDashboardViewSet) ...

class MyCoursesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        enrolled_courses = Course.objects.filter(
            enrollments__user=user
        ).order_by('-enrollments__enrolled_at')
        
        # Filter by progress
        progress = self.request.query_params.get('progress', None)
        if progress == 'completed':
            enrollments = Enrollment.objects.filter(user=user, is_completed=True)
            course_ids = enrollments.values_list('course_id', flat=True)
            enrolled_courses = enrolled_courses.filter(id__in=course_ids)
        elif progress == 'in_progress':
            enrollments = Enrollment.objects.filter(user=user, is_completed=False)
            course_ids = enrollments.values_list('course_id', flat=True)
            enrolled_courses = enrolled_courses.filter(id__in=course_ids)
        
        return enrolled_courses

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        user = request.user
        
        # User stats
        enrolled_courses = Enrollment.objects.filter(user=user).count()
        completed_courses = Enrollment.objects.filter(user=user, is_completed=True).count()
        total_progress = Enrollment.objects.filter(user=user).aggregate(
            avg_progress=Avg('progress')
        )['avg_progress'] or 0
        
        # Recent enrollments
        recent_enrollments = Enrollment.objects.filter(
            user=user
        ).order_by('-enrolled_at')[:5]
        
        # Course recommendations (based on categories of enrolled courses)
        user_categories = Category.objects.filter(
            courses__enrollments__user=user
        ).distinct()
        
        recommended_courses = Course.objects.filter(
            categories__in=user_categories
        ).exclude(
            enrollments__user=user
        ).distinct().order_by('-average_rating')[:6]
        
        return Response({
            'status': 'success',
            'data': {
                'stats': {
                    'enrolled_courses': enrolled_courses,
                    'completed_courses': completed_courses,
                    'total_progress': round(total_progress, 1),
                    'completion_rate': round((completed_courses / enrolled_courses * 100) if enrolled_courses > 0 else 0, 1)
                },
                'recent_enrollments': EnrollmentSerializer(recent_enrollments, many=True).data,
                'recommended_courses': CourseListSerializer(
                    recommended_courses, 
                    many=True,
                    context={'request': request}
                ).data
            }
        })

# Instructor views
class InstructorCoursesViewSet(viewsets.ModelViewSet):
    serializer_class = CourseCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

class InstructorDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        instructor = request.user
        
        # Instructor stats
        total_courses = Course.objects.filter(instructor=instructor).count()
        published_courses = Course.objects.filter(instructor=instructor, status='published').count()
        total_students = Enrollment.objects.filter(
            course__instructor=instructor
        ).values('user').distinct().count()
        total_earnings = Enrollment.objects.filter(
            course__instructor=instructor,
            course__price__gt=0
        ).aggregate(
            total=models.Sum('course__price')
        )['total'] or 0
        
        # Recent courses
        recent_courses = Course.objects.filter(
            instructor=instructor
        ).order_by('-created_at')[:5]
        
        # Top performing courses
        top_courses = Course.objects.filter(
            instructor=instructor,
            status='published'
        ).annotate(
            student_count=Count('enrollments')
        ).order_by('-student_count')[:5]
        
        return Response({
            'status': 'success',
            'data': {
                'stats': {
                    'total_courses': total_courses,
                    'published_courses': published_courses,
                    'total_students': total_students,
                    'total_earnings': float(total_earnings)
                },
                'recent_courses': CourseListSerializer(recent_courses, many=True).data,
                'top_courses': CourseListSerializer(top_courses, many=True).data
            }
        })
    

# courses/views.py

from .models import SavedCourse
from .serializers import SavedCourseSerializer, SavedCourseCreateSerializer

class SavedCourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SavedCourseSerializer

    def get_queryset(self):
        # Faqat joriy foydalanuvchining saqlangan kurslari
        return SavedCourse.objects.filter(user=self.request.user).order_by('-saved_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return SavedCourseCreateSerializer
        return SavedCourseSerializer

    def perform_create(self, serializer):
        # Takroriy saqlashni oldini olish (unique_together bilan DRF ham tekshiradi)
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['delete'], url_path='(?P<course_id>\d+)')
    def unsave(self, request, course_id=None):
        """Muayyan kursni saqlanganlardan olib tashlash"""
        try:
            saved = SavedCourse.objects.get(user=request.user, course_id=course_id)
            saved.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SavedCourse.DoesNotExist:
            return Response({'error': 'Bu kurs saqlanmagan.'}, status=status.HTTP_404_NOT_REQUIRED)

    @action(detail=False, methods=['get'])
    def ids(self, request):
        """Faqat saqlangan kurs IDlarini qaytaradi (frontend uchun foydali)"""
        ids = self.get_queryset().values_list('course_id', flat=True)
        return Response(list(ids))