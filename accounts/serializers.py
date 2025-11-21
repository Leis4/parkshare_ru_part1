# accounts/serializers.py

from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.utils import normalize_phone
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Базовое представление пользователя для админских API.
    Контактные данные не раскрываются.
    """

    has_email = serializers.SerializerMethodField()
    has_phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "role",
            "is_active",
            "date_joined",
            "has_email",
            "has_phone",
        )

    def get_has_email(self, obj: User) -> bool:
        return bool(obj.email_plain)

    def get_has_phone(self, obj: User) -> bool:
        return bool(obj.phone_plain)


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Профиль текущего пользователя.
    Здесь можно редактировать email/телефон.
    """

    email = serializers.CharField(
        source="email_plain", allow_blank=True, required=False
    )
    phone = serializers.CharField(
        source="phone_plain", allow_blank=True, required=False
    )

    class Meta:
        model = User
        fields = ("id", "username", "role", "email", "phone")

    def validate_phone(self, value: str) -> str:
        return normalize_phone(value)


class RegisterSerializer(serializers.Serializer):
    """
    Регистрация через API.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                _("Пользователь с таким логином уже существует.")
            )
        return value

    def validate_phone(self, value: str) -> str:
        return normalize_phone(value)

    def create(self, validated_data: dict) -> User:
        email = validated_data.pop("email", "")
        phone = validated_data.pop("phone", "")
        user = User(username=validated_data["username"])
        user.set_password(validated_data["password"])
        if email:
            user.email_plain = email
        if phone:
            user.phone_plain = phone
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """
    Логин через API (session-based).
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        username = attrs.get("username")
        password = attrs.get("password")
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError(
                    _("Неверный логин или пароль."), code="authorization"
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    _("Пользователь деактивирован."), code="authorization"
                )
            attrs["user"] = user
            return attrs
        raise serializers.ValidationError(
            _("Необходимо указать логин и пароль."), code="authorization"
        )
