from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, RegistrationViewSet, TeamRegistrationViewSet

router = DefaultRouter()
router.register('students', StudentViewSet, basename='student')
router.register('registrations', RegistrationViewSet, basename='registration')
router.register('team-registrations', TeamRegistrationViewSet, basename='team-registration')

urlpatterns = [
    path('', include(router.urls)),
]
