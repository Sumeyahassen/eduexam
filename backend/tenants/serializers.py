from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Institution, User


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ["id", "name", "type", "slug", "contact", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "role", "institution"]
        read_only_fields = ["id"]


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name",
                  "password", "role", "institution"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class EduExamTokenSerializer(TokenObtainPairSerializer):
    """Adds role and institution_slug to the JWT response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["institution_slug"] = (
            user.institution.slug if user.institution else None
        )
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["institution_slug"] = (
            self.user.institution.slug if self.user.institution else None
        )
        return data
