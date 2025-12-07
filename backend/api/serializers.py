from rest_framework import serializers
from .models import Challenge, Result

class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = '__all__'

class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ["id", "challenge", "is_correct", "score", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        # Attach the logged-in user automatically
        user = self.context["request"].user
        return Result.objects.create(user=user, **validated_data)