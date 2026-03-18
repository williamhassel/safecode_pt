import random
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Challenge, Result, Certificate, GenerationRequest, GeneratedChallenge, ChallengeSet, ChallengeSetItem
from .serializers import ChallengeSerializer, ResultSerializer, UserSerializer, RegisterSerializer
from .utils import check_and_issue_certificate, get_user_stats, check_and_issue_certificate_sets
from .tasks import generate_challenge, fill_review_queue, fill_review_queue_for_type, VULNERABILITY_TYPES


class IsStaffUser(permissions.BasePermission):
    """Allow access only to staff/admin users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


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
        has_certificate = Certificate.objects.filter(user=user).exists()
        completed_sets = ChallengeSet.objects.filter(user=user, is_passed=True).count()

        return Response({
            "total_answered": total,
            "correct_answers": correct,
            "accuracy": accuracy,
            "has_certificate": has_certificate,
            "completed_sets": completed_sets,
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
        return Response({"id": ch.id, **ch.artifact})


class LatestChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Fetch the most recently generated challenge"""
        ch = GeneratedChallenge.objects.order_by('-id').first()
        if not ch:
            return Response({"error": "No challenges available"}, status=404)
        # Include the ID along with the artifact data
        return Response({"id": ch.id, **ch.artifact})


class NextChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Serve a random pooled challenge the user hasn't seen yet."""
        user = request.user
        seen_ids = Result.objects.filter(
            user=user,
            generated_challenge__isnull=False
        ).values_list("generated_challenge_id", flat=True)

        available = GeneratedChallenge.objects.filter(
            is_pooled=True
        ).exclude(id__in=seen_ids)

        if not available.exists():
            # User has seen everything — reset and serve from full pool
            available = GeneratedChallenge.objects.filter(is_pooled=True)

        if not available.exists():
            return Response({"error": "No challenges available yet. Please try again shortly."}, status=404)

        ch = random.choice(list(available.values_list("id", flat=True)))
        ch = GeneratedChallenge.objects.get(id=ch)
        return Response({"id": ch.id, **ch.artifact})


# ---------------------------------------------------------------------------
# Admin review queue endpoints (staff only)
# ---------------------------------------------------------------------------

class AdminReviewQueueView(APIView):
    """List pending-review challenges and trigger queue refill."""
    permission_classes = [IsStaffUser]

    def get(self, request):
        pending_qs = GeneratedChallenge.objects.filter(
            status='pending_review'
        ).order_by('created_at')[:10]

        challenges = []
        for ch in pending_qs:
            challenges.append({
                "id": ch.id,
                "vuln_type": ch.vuln_type,
                "difficulty": ch.difficulty,
                "language": ch.language,
                "created_at": ch.created_at.isoformat(),
                **ch.artifact,
            })

        pending_count = GeneratedChallenge.objects.filter(status='pending_review').count()
        approved_count = GeneratedChallenge.objects.filter(status='approved', is_pooled=True).count()

        # Auto-trigger generation when queue runs low
        if pending_count < 5:
            fill_review_queue.delay()

        return Response({
            "challenges": challenges,
            "pending_count": pending_count,
            "approved_count": approved_count,
        })

    def post(self, request):
        """Manually trigger generation of review-queue challenges."""
        fill_review_queue.delay()
        return Response({"status": "generation triggered"})


class AdminChallengeApproveView(APIView):
    """Approve a pending-review challenge and add it to the student pool."""
    permission_classes = [IsStaffUser]

    def post(self, request, challenge_id):
        ch = get_object_or_404(GeneratedChallenge, id=challenge_id)
        if ch.status != 'pending_review':
            return Response(
                {"error": "Challenge is not pending review"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ch.status = 'approved'
        ch.is_pooled = True
        ch.save(update_fields=['status', 'is_pooled'])

        # Keep queue topped up
        if GeneratedChallenge.objects.filter(status='pending_review').count() < 5:
            fill_review_queue.delay()

        return Response({"status": "approved", "id": ch.id})


class AdminChallengeDiscardView(APIView):
    """Discard a pending-review challenge (remove from queue without pooling)."""
    permission_classes = [IsStaffUser]

    def post(self, request, challenge_id):
        ch = get_object_or_404(GeneratedChallenge, id=challenge_id)
        if ch.status != 'pending_review':
            return Response(
                {"error": "Challenge is not pending review"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ch.status = 'discarded'
        ch.save(update_fields=['status'])

        # Keep queue topped up
        if GeneratedChallenge.objects.filter(status='pending_review').count() < 5:
            fill_review_queue.delay()

        return Response({"status": "discarded", "id": ch.id})


class AdminGenerateBatchView(APIView):
    """Generate N challenges of a specific vulnerability type for the admin review queue."""
    permission_classes = [IsStaffUser]

    def post(self, request):
        vuln_type = request.data.get("vuln_type")
        count = int(request.data.get("count", 10))

        if not vuln_type:
            return Response({"error": "vuln_type is required"}, status=status.HTTP_400_BAD_REQUEST)
        if vuln_type not in VULNERABILITY_TYPES:
            return Response(
                {"error": f"Unknown vuln_type '{vuln_type}'. Valid types: {VULNERABILITY_TYPES}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fill_review_queue_for_type.delay(vuln_type, count)
        return Response({"status": "generation triggered", "vuln_type": vuln_type, "count": count})


class AdminPoolStatsView(APIView):
    """Quick stats snapshot for the admin dashboard."""
    permission_classes = [IsStaffUser]

    def get(self, request):
        return Response({
            "pending_review": GeneratedChallenge.objects.filter(status='pending_review').count(),
            "approved": GeneratedChallenge.objects.filter(status='approved', is_pooled=True).count(),
            "discarded": GeneratedChallenge.objects.filter(status='discarded').count(),
        })


# ---------------------------------------------------------------------------
# Challenge set endpoints
# ---------------------------------------------------------------------------

SET_SIZE = 10
REQUIRED_SETS_FOR_CERT = 10


class SetNewView(APIView):
    """Start a new set of SET_SIZE challenges for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Prefer challenges the user hasn't seen in any previous set
        seen_ids = ChallengeSetItem.objects.filter(
            challenge_set__user=user
        ).values_list('challenge_id', flat=True)

        available = GeneratedChallenge.objects.filter(is_pooled=True).exclude(id__in=seen_ids)

        if available.count() < SET_SIZE:
            # Fall back to full pool when the user has seen most challenges
            available = GeneratedChallenge.objects.filter(is_pooled=True)

        if available.count() < SET_SIZE:
            return Response(
                {"error": "Not enough challenges in pool. Please check back soon."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ids = random.sample(list(available.values_list('id', flat=True)), SET_SIZE)
        challenges_map = {ch.id: ch for ch in GeneratedChallenge.objects.filter(id__in=ids)}

        challenge_set = ChallengeSet.objects.create(user=user)
        for position, cid in enumerate(ids):
            ChallengeSetItem.objects.create(
                challenge_set=challenge_set,
                challenge_id=cid,
                position=position,
            )

        serialized = [{"id": challenges_map[cid].id, **challenges_map[cid].artifact} for cid in ids]
        return Response({"set_id": challenge_set.id, "challenges": serialized})


class SetSubmitView(APIView):
    """Submit answers for a completed challenge set."""
    permission_classes = [IsAuthenticated]

    def post(self, request, set_id):
        user = request.user
        challenge_set = get_object_or_404(ChallengeSet, id=set_id, user=user)

        if challenge_set.completed_at is not None:
            return Response({"error": "Set already submitted."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get('answers', [])
        items = {item.challenge_id: item for item in challenge_set.items.all()}

        score = 0
        for answer in answers:
            cid = int(answer['challenge_id'])
            is_correct = bool(answer['is_correct'])

            if cid in items:
                item = items[cid]
                item.is_correct = is_correct
                item.save(update_fields=['is_correct'])

            Result.objects.create(
                user=user,
                generated_challenge_id=cid,
                is_correct=is_correct,
                score=1 if is_correct else 0,
            )

            if is_correct:
                score += 1

        total = len(answers)
        is_passed = (score / total) >= 0.8 if total > 0 else False

        challenge_set.completed_at = timezone.now()
        challenge_set.is_passed = is_passed
        challenge_set.score = score
        challenge_set.total = total
        challenge_set.save()

        completed_sets = ChallengeSet.objects.filter(user=user, is_passed=True).count()
        certificate = check_and_issue_certificate_sets(user, required_sets=REQUIRED_SETS_FOR_CERT)

        return Response({
            "score": score,
            "total": total,
            "is_passed": is_passed,
            "completed_sets": completed_sets,
            "certificate_issued": certificate is not None,
        })
