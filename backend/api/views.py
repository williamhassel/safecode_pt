from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Challenge, Result
from .serializers import ChallengeSerializer, ResultSerializer

class ChallengeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.AllowAny]

class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [permissions.IsAuthenticated]
