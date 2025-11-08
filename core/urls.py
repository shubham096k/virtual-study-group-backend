from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, ProfileView, GroupViewSet, TaskViewSet,
    DocumentViewSet, StudySessionViewSet, TimerSessionViewSet, NotificationViewSet, DocumentCommentViewSet,

)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'sessions', StudySessionViewSet, basename='session')
# router.register(r'timers', TimerSessionViewSet, basename='timer')
# router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'document-comments', DocumentCommentViewSet, basename='documentcomment')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('', include(router.urls)),
]
