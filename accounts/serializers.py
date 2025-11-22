# accounts/serializers.py

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.utils import normalize_phone
from .auth import find_user_by_identifier
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
        value = normalize_phone(value)
        user = self.instance
        if not value:
            return ""
        qs = User.objects.filter(phone_encrypted=value)
        if user is not None:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError(
                _("Пользователь с таким телефоном уже существует.")
            )
        return value

    def validate_email(self, value: str) -> str:
        value = (value or "").strip().lower()
        if not value:
            return ""
        user = self.instance
        qs = User.objects.filter(email_encrypted=value)
        if user is not None:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError(
                _("Пользователь с таким email уже существует.")
            )
        return value


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

    def validate_email(self, value: str) -> str:
        value = (value or "").strip().lower()
        if not value:
            return ""
        if User.objects.filter(email_encrypted=value).exists():
            raise serializers.ValidationError(
                _("Пользователь с таким email уже зарегистрирован.")
            )
        return value

    def validate_phone(self, value: str) -> str:
        value = normalize_phone(value)
        if not value:
            return ""
        if User.objects.filter(phone_encrypted=value).exists():
            raise serializers.ValidationError(
                _("Пользователь с таким телефоном уже зарегистрирован.")
            )
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

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
    Позволяет использовать логин, email или телефон.
    """

    identifier = serializers.CharField(
        label=_("Логин / Email / Телефон"),
    )
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        if not identifier or not password:
            raise serializers.ValidationError(
                _("Необходимо указать логин и пароль."), code="authorization"
            )

        user = find_user_by_identifier(identifier)
        if not user or not user.check_password(password):
            raise serializers.ValidationError(
                _("Неверный логин (имя, email или телефон) или пароль."),
                code="authorization",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                _("Пользователь деактивирован."), code="authorization"
            )

        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Смена пароля текущего пользователя.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        user = self.context["request"].user
        validate_password(value, user=user)
        return value

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        old_password = attrs.get("old_password")
        if not user.check_password(old_password):
            raise serializers.ValidationError(
                {"old_password": _("Неверный текущий пароль.")}
            )
        return attrs

    def save(self, **kwargs) -> User:
        user = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Запрос на сброс пароля по email (API).
    """

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        value = (value or "").strip().lower()
        # В целях безопасности не раскрываем, существует ли пользователь.
        return value
