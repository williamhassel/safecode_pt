# backend/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from backend.api.views import (
    ChallengeViewSet,
    ResultViewSet,      # keep only if you actually use it elsewhere
    ResultCreateView,
    RegisterView,
    CurrentUserView,
    UserStatsView,
    GeneratorGenerateView,
    GeneratorStatusView,
    GeneratorChallengeView,
)

router = routers.DefaultRouter()
router.register(r'challenges', ChallengeViewSet)
# If you ONLY use ResultCreateView, you can comment this out:
# router.register(r'results', ResultViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Router endpoints, e.g. /api/challenges/
    path('api/', include(router.urls)),

    # Auth API
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('api/auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('api/stats/', UserStatsView.as_view(), name='user-stats'),

    # Result creation + stats + certificate
    path('api/results/', ResultCreateView.as_view(), name='result-create'),

    path('api/generator/generate/', GeneratorGenerateView.as_view(), name='generator-generate'),
    path('api/generator/generation/<int:generation_id>/', GeneratorStatusView.as_view(), name='generator-status'),
    path('api/generator/challenge/<int:challenge_id>/', GeneratorChallengeView.as_view(), name='generator-challenge'),
]
