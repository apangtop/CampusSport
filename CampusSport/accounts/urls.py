from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView, CheckedTokenRefreshView, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

from .school_views import BrandingView, SchoolProfileView, SchoolDirectoryView

urlpatterns = [
    path('school/branding/', BrandingView.as_view(), name='school-branding'),
    path('school/profile/', SchoolProfileView.as_view(), name='school-profile'),
    path('school/directory/', SchoolDirectoryView.as_view(), name='school-directory'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CheckedTokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
