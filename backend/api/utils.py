from django.db.models import Count
from .models import Result, Certificate


def get_user_stats(user):
    qs = Result.objects.filter(user=user)
    total = qs.count()
    correct = qs.filter(is_correct=True).count()
    accuracy = (correct / total) if total > 0 else 0.0
    return total, correct, accuracy


def check_and_issue_certificate(user, min_questions=100, threshold=0.80):
    total, correct, accuracy = get_user_stats(user)

    if total < min_questions or accuracy < threshold:
        return None

    # avoid duplicate certs for same rule
    already_has = Certificate.objects.filter(
        user=user,
        min_questions=min_questions,
        threshold_accuracy=threshold,
    ).exists()

    if already_has:
        return None

    return Certificate.objects.create(
        user=user,
        threshold_accuracy=threshold,
        min_questions=min_questions,
        accuracy_at_issue=accuracy,
        total_questions_at_issue=total,
    )


def check_and_issue_certificate_sets(user, required_sets=10):
    """Issue a certificate when the user has completed `required_sets` passed sets."""
    from .models import ChallengeSet
    completed = ChallengeSet.objects.filter(user=user, is_passed=True).count()

    if completed < required_sets:
        return None

    already_has = Certificate.objects.filter(
        user=user,
        min_questions=required_sets,
        threshold_accuracy=0.80,
    ).exists()

    if already_has:
        return None

    total_questions = Result.objects.filter(user=user).count()
    return Certificate.objects.create(
        user=user,
        threshold_accuracy=0.80,
        min_questions=required_sets,
        accuracy_at_issue=float(completed) / required_sets,
        total_questions_at_issue=total_questions,
    )
