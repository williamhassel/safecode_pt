from rest_framework import serializers
from .models import Challenge, Result
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = '__all__'

class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ["id", "challenge", "generated_challenge", "is_correct", "score", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        # Attach the logged-in user automatically
        user = self.context["request"].user
        return Result.objects.create(user=user, **validated_data)