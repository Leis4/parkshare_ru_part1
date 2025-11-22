# accounts/views.py

from typing import Any

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.forms import PasswordResetForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import UpdateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsSelfOrAdmin
from .forms import LoginForm, ProfileForm, RegisterForm
from .models import User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
)


# ===== HTML-вьюхи (шаблонный интерфейс) =====


class RegisterView(View):
    """
    Регистрация пользователя через HTML-форму.
    """

    template_name = "accounts/register.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("user_dashboard")
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("user_dashboard")
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("user_dashboard")
        return render(request, self.template_name, {"form": form})


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Редактирование профиля (email/телефон) в HTML-интерфейсе.
    """

    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("user_dashboard")

    def get_object(self, queryset=None) -> User:
        return self.request.user


class CustomLoginView(DjangoLoginView):
    """
    Обёртка над стандартным LoginView с русским шаблоном и кастомной формой.
    """

    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_success_url(self) -> str:
        return reverse("user_dashboard")


def logout_view(request: HttpRequest) -> HttpResponse:
    auth_logout(request)
    return redirect("landing")


# ===== API (DRF) =====


class UserViewSet(viewsets.ModelViewSet):
    """
    API для работы с пользователями.

    Маршруты:
    - /api/accounts/users/                   (GET)   — список (только админ)
    - /api/accounts/users/{id}/              (GET)   — профиль (сам или админ)
    - /api/accounts/users/me/                (GET)   — профиль текущего пользователя
    - /api/accounts/users/me/                (PATCH) — обновление своего профиля
    - /api/accounts/users/register/          (POST)  — регистрация
    - /api/accounts/users/login/             (POST)  — логин (session-based)
    - /api/accounts/users/logout/            (POST)  — логаут
    - /api/accounts/users/change-password/   (POST)  — смена пароля (API)
    - /api/accounts/users/reset-password/    (POST)  — запрос сброса пароля по email
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

    def get_permissions(self) -> list[Any]:
        if self.action in ("register", "login", "reset_password"):
            permission_classes = [permissions.AllowAny]
        elif self.action in ("list", "destroy"):
            permission_classes = [permissions.IsAdminUser]
        elif self.action in ("me", "change_password", "logout"):
            permission_classes = [permissions.IsAuthenticated]
        else:
            # retrieve/update/partial_update — только сам пользователь или админ
            permission_classes = [permissions.IsAuthenticated, IsSelfOrAdmin]
        return [perm() for perm in permission_classes]

    def get_queryset(self):
        user: User = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        if user.is_superuser or getattr(user, "is_admin", False):
            return User.objects.all().order_by("-date_joined")
        return User.objects.filter(pk=user.pk)

    def perform_destroy(self, instance: User) -> None:
        """
        Удалять пользователей может только админ — контролируется permissions.
        """
        super().perform_destroy(instance)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        """
        Профиль текущего пользователя.
        GET — получить; PATCH — обновить email/телефон.
        """
        if request.method.lower() == "get":
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        """
        Регистрация пользователя через API.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = serializer.save()
        auth_login(request, user)
        data = UserProfileSerializer(user).data
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """
        Логин через API. Используются стандартные Django-сессии.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = serializer.validated_data["user"]
        auth_login(request, user)
        data = UserProfileSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        """
        Логаут через API (очистка сессии).
        """
        auth_logout(request)
        return Response(
            {"detail": "Вы вышли из системы."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """
        Смена пароля текущего пользователя (API).
        """
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Пароль успешно изменён."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        """
        Запрос на сброс пароля по email (API).

        Использует стандартный PasswordResetForm и отправляет письмо
        через настроенный EMAIL_BACKEND.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        form = PasswordResetForm(data={"email": email})
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="accounts/password_reset_email.txt",
                subject_template_name="accounts/password_reset_subject.txt",
            )

        # Независимо от результата говорим одно и то же, чтобы не раскрывать,
        # существует ли пользователь с таким email.
        return Response(
            {
                "detail": (
                    "Если пользователь с таким email существует, на него отправлена "
                    "инструкция по сбросу пароля."
                )
            },
            status=status.HTTP_200_OK,
        )
