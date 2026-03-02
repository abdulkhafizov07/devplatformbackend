# courses/admin.py
from django.contrib import admin
from .models import Category, Course, Episode, Enrollment, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('title', 'order', 'duration', 'is_free', 'is_active')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'instructor', 'level', 'price', 'status', 'created_at')
    list_filter = ('status', 'level', 'is_featured', 'is_free', 'categories')
    search_fields = ('title', 'description', 'instructor__username')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories',)  # ✅ 'students' ni olib tashladik
    readonly_fields = ('total_lessons', 'total_duration', 'average_rating', 'total_reviews')
    inlines = [EpisodeInline]
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'slug', 'description', 'short_description', 'thumbnail', 'iframe')
        }),
        ('Kategoriyalar', {
            'fields': ('categories',)
        }),
        ('O\'qituvchi', {
            'fields': ('instructor',)
        }),
        ('Narx va daraja', {
            'fields': ('level', 'duration', 'price', 'discount_price', 'is_free')
        }),
        ('Statistika', {
            'fields': ('total_lessons', 'total_duration', 'average_rating', 'total_reviews')
        }),
        ('Status', {
            'fields': ('is_featured', 'status', 'published_at')
        }),
    )

@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'duration', 'is_free', 'is_active')
    list_filter = ('is_free', 'is_active', 'course')
    search_fields = ('title', 'description', 'course__title')
    ordering = ('course', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress', 'is_completed', 'enrolled_at')
    list_filter = ('is_completed', 'course')
    search_fields = ('user__username', 'course__title')
    filter_horizontal = ('completed_episodes',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'course')
    search_fields = ('user__username', 'course__title', 'comment')
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} ta baho tasdiqlandi.")
    approve_reviews.short_description = "Tanlangan baholarni tasdiqlash"

    