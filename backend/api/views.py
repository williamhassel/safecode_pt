from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import Challenge, Result, Certificate, GenerationRequest, GeneratedChallenge
from .serializers import ChallengeSerializer, ResultSerializer, UserSerializer, RegisterSerializer
from .utils import check_and_issue_certificate, get_user_stats
from .tasks import generate_challenge


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        total, correct, accuracy = get_user_stats(user)

        # Check if user has earned certificate (8/10 requirement)
        has_certificate = Certificate.objects.filter(user=user).exists()

        return Response({
            "total_answered": total,
            "correct_answers": correct,
            "accuracy": accuracy,
            "has_certificate": has_certificate,
        })


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        user = request.user
        certificate = check_and_issue_certificate(user, min_questions=10, threshold=0.80)
        total, correct, accuracy = get_user_stats(user)

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


class GeneratorGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        gr = GenerationRequest.objects.create(created_by=request.user, status="queued")
        generate_challenge.delay(gr.id)
        return Response({"generation_id": gr.id, "status": gr.status})


class GeneratorStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, generation_id: int):
        gr = get_object_or_404(GenerationRequest, id=generation_id)
        payload = {"id": gr.id, "status": gr.status, "error": gr.error}
        if gr.status == "done" and hasattr(gr, "challenge"):
            payload["challenge_id"] = gr.challenge.id
        return Response(payload)


class GeneratorChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, challenge_id: int):
        ch = get_object_or_404(GeneratedChallenge, id=challenge_id)
        return Response(ch.artifact)
