from django.shortcuts import render

# # Create your views here.
# from rest_framework import viewsets, generics, permissions
# from .models import Challenge, Result
# from .serializers import ChallengeSerializer, ResultSerializer, UserSerializer, RegisterSerializer
# from .utils import check_and_issue_certificate, get_user_stats

# from rest_framework import generics, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated

# from django.contrib.auth.models import User

# Create your views here.
from rest_framework import viewsets, generics, permissions
from .models import Challenge, Result
from .serializers import ChallengeSerializer, ResultSerializer, UserSerializer, RegisterSerializer
from .utils import check_and_issue_certificate, get_user_stats

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth.models import User



class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Body: { "username": "...", "email": "...", "password": "..." }
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class CurrentUserView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    Returns info about the logged-in user.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChallengeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.AllowAny]

class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [permissions.IsAuthenticated]

class ResultCreateView(generics.CreateAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Let DRF handle validation + saving first
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # After saving the result: update stats and maybe issue certificate
        user = request.user
        certificate = check_and_issue_certificate(user, min_questions=100, threshold=0.80)
        total, correct, accuracy = get_user_stats(user)

        # Build custom response
        response_data = {
            "result": serializer.data,
            "stats": {
                "total_answered": total,
                "correct_answers": correct,
                "accuracy": accuracy,
            },
            "certificate_issued": certificate is not None,
        }

        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)