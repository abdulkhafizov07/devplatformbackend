# courses/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count, Sum
from django.utils import timezone
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # ✅ Qo'shildi
    order = models.IntegerField(default=0)  # ✅ Qo'shildi
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Boshlang\'ich'),
        ('intermediate', 'O\'rtacha'),
        ('advanced', 'Murakkab'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Qoralama'),
        ('published', 'Nashr etilgan'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)
    iframe = models.TextField(help_text="Asosiy kurs video embed kodi (iframe)", blank=True)
    
    # Categories
    categories = models.ManyToManyField(Category, related_name='courses', blank=True)
    
    # Course details
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='courses_taught')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration = models.IntegerField(help_text="Kurs davomiyligi (soat)", default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stats
    total_lessons = models.IntegerField(default=0)
    total_duration = models.IntegerField(default=0, help_text="Jami davomiylik (daqiqa)")
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    total_students = models.IntegerField(default=0)  # ✅ Qo'shildi
    
    # Meta
    is_featured = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Agar kurs nashr etilgan bo'lsa, published_at ni o'rnatish
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_discounted(self):
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def current_price(self):
        return self.discount_price if self.is_discounted else self.price

    def update_stats(self):
        """Kurs statistikasini yangilash"""
        self.total_lessons = self.episodes.filter(is_active=True).count()
        
        # Jami davomiylikni hisoblash
        total_duration = self.episodes.filter(is_active=True).aggregate(
            total=models.Sum('duration')
        )['total'] or 0
        self.total_duration = total_duration
        
        # Baholarni yangilash
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
            self.average_rating = round(avg_rating, 1)
            self.total_reviews = reviews.count()
        else:
            self.average_rating = 0.0
            self.total_reviews = 0
            
        # Talabalar sonini yangilash
        self.total_students = self.enrollments.filter(is_active=True).count()
        
        self.save(update_fields=[
            'total_lessons', 'total_duration', 'average_rating', 
            'total_reviews', 'total_students'
        ])

class Episode(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='episodes')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    iframe = models.TextField(help_text="Video embed kodi (iframe)", blank=True)
    duration = models.IntegerField(help_text="Daqiqalarda", default=0)
    order = models.IntegerField(default=0)
    is_free = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Resources
    attachment = models.FileField(upload_to='episode_attachments/', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['course', 'slug']
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    completed_episodes = models.ManyToManyField(Episode, blank=True, related_name='completions')
    progress = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # ✅ Qo'shildi
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'course']

    def update_progress(self):
        total_episodes = self.course.episodes.filter(is_active=True).count()
        if total_episodes > 0:
            completed = self.completed_episodes.count()
            self.progress = (completed / total_episodes) * 100
            self.is_completed = self.progress >= 100
            if self.is_completed and not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.progress = 0
            self.is_completed = False
            
        self.save()

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 - Juda yomon'),
        (2, '2 - Yomon'),
        (3, '3 - O\'rtacha'),
        (4, '4 - Yaxshi'),
        (5, '5 - A\'lo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Kurs bahosini yangilash
        self.course.update_stats()

# Signal handlers
@receiver(pre_save, sender=Course)
def generate_course_slug(sender, instance, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.title)
        slug = base_slug
        counter = 1
        while Course.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug

@receiver(pre_save, sender=Episode)
def generate_episode_slug(sender, instance, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.title)
        slug = base_slug
        counter = 1
        while Episode.objects.filter(course=instance.course, slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug

# Enrollment yaratilganda kurs statistikasini yangilash
@receiver(post_save, sender=Enrollment)
def update_course_stats_on_enrollment(sender, instance, created, **kwargs):
    if created:
        instance.course.update_stats()

# Enrollment o'chirilganda kurs statistikasini yangilash
@receiver(post_delete, sender=Enrollment)
def update_course_stats_on_enrollment_delete(sender, instance, **kwargs):
    instance.course.update_stats()



    # courses/models.py

class SavedCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'course']   # Bir foydalanuvchi bir kursni faqat bir marta saqlay oladi
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} -> {self.course.title}"
    
    