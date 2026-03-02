# courses/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, EpisodeViewSet,
    ReviewViewSet, MyCoursesViewSet, DashboardViewSet,
    InstructorCoursesViewSet, InstructorDashboardViewSet,SavedCourseViewSet
)

# Asosiy router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'my-courses', MyCoursesViewSet, basename='my-courses')
router.register(r'instructor/courses', InstructorCoursesViewSet, basename='instructor-courses')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'instructor/dashboard', InstructorDashboardViewSet, basename='instructor-dashboard')

router.register(r'saved-courses', SavedCourseViewSet, basename='saved-course')

# Nested router uchun patternlar
nested_patterns = [
    path('courses/<slug:course_slug>/episodes/', 
         EpisodeViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='course-episodes-list'),
    path('courses/<slug:course_slug>/episodes/<slug:slug>/', 
         EpisodeViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='course-episodes-detail'),
    path('courses/<slug:course_slug>/reviews/', 
         ReviewViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='course-reviews-list'),
    path('courses/<slug:course_slug>/reviews/<int:pk>/', 
         ReviewViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='course-reviews-detail'),
         
]

urlpatterns = [
    path('', include(router.urls)),
    path('', include(nested_patterns)),
]