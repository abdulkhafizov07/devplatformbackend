from django.urls import path
from .views import RegisterView, LoginView, ProfileView, ChangePasswordView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
]