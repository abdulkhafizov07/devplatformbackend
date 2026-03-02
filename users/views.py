from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    UserUpdateSerializer
)
from django.contrib.auth import authenticate
import json

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'data': {
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Email orqali ham login qilish imkoniyati
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'User with this email does not exist.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'status': 'success',
                    'data': {
                        'user': UserSerializer(user).data,
                        'tokens': {
                            'access': str(refresh.access_token),
                            'refresh': str(refresh)
                        }
                    }
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid credentials.'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'status': 'error',
                'message': 'Email and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'data': UserSerializer(request.user).data
            })
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        return self.put(request)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({
                'status': 'error',
                'message': 'Old password is incorrect.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'status': 'success',
            'message': 'Password changed successfully.'
        })
    

    