from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
import uuid

class Challenge(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
        ],
        default='easy',
    )

    def __str__(self):
        return self.title


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)

    is_correct = models.BooleanField(default=False)

    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}: {self.score}"

    # Optional: if you only want one result per user/challenge (e.g. best attempt)
    # remove this if you want to allow multiple attempts!
    # unique_together = ('user', 'challenge')
    class Meta:

        pass


class Certificate(models.Model):
    """
    A certificate issued to a user once they reach
    e.g. at least 100 answered questions and 80% accuracy.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certificates',
    )

    issued_at = models.DateTimeField(auto_now_add=True)

    # The rule used when issuing the cert (for traceability)
    threshold_accuracy = models.FloatField()        # e.g. 0.80
    min_questions = models.PositiveIntegerField()   # e.g. 100

    # What the user had actually achieved when it was issued
    accuracy_at_issue = models.FloatField()
    total_questions_at_issue = models.PositiveIntegerField()

    # For verification links / codes on the certificate
    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    def __str__(self):
        return f"Certificate for {self.user.username} @ {self.issued_at.date()}"