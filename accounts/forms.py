# accounts/forms.py

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from core.utils import normalize_phone
from .models import User
from .utils import normalize_email, hash_email, hash_phone


class LoginForm(AuthenticationForm):
    """
    HTML-форма логина (username + пароль).
    Логика поиска по email/телефону заложена в API и LoginSerializer.
    """

    username = forms.CharField(
        label=_("Логин"),
        widget=forms.TextInput(attrs={"class": "ps-input", "autocomplete": "username"}),
    )
    password = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(
            attrs={"class": "ps-input", "autocomplete": "current-password"}
        ),
    )

    def confirm_login_allowed(self, user: User) -> None:
        if not user.is_active:
            raise forms.ValidationError(
                _("Аккаунт деактивирован. Обратитесь в поддержку."),
                code="inactive",
            )


class RegisterForm(UserCreationForm):
    """
    HTML‑регистрация: username + (опционально) email и телефон.
    Email/телефон хранятся в зашифрованных полях, но уникальность проверяем
    по хэшам email_hash / phone_hash.
    """

    email = forms.EmailField(
        label=_("Email (опционально)"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "ps-input", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label=_("Телефон (опционально)"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "ps-input",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "ps-input", "autocomplete": "username"}
            ),
        }

    def clean_email(self) -> str:
        """
        Нормализуем email и проверяем уникальность по email_hash.
        """
        raw_email = self.cleaned_data.get("email")
        email = normalize_email(raw_email)
        if not email:
            return ""

        email_hash = hash_email(email)
        if email_hash and User.objects.filter(email_hash=email_hash).exists():
            raise forms.ValidationError(
                _("Пользователь с таким email уже зарегистрирован.")
            )
        return email

    def clean_phone(self) -> str:
        """
        Нормализуем телефон и проверяем уникальность по phone_hash.
        """
        raw_phone = self.cleaned_data.get("phone") or ""
        if not raw_phone:
            return ""

        phone = normalize_phone(raw_phone)
        if not phone:
            raise forms.ValidationError(_("Некорректный формат телефона."))

        phone_hash = hash_phone(phone)
        if phone_hash and User.objects.filter(phone_hash=phone_hash).exists():
            raise forms.ValidationError(
                _("Пользователь с таким телефоном уже зарегистрирован.")
            )
        return phone

    def save(self, commit: bool = True) -> User:
        """
        Сохраняем пользователя:
        - username/пароль — стандартно;
        - email/phone пишем в email_plain/phone_plain (зашифрованные поля),
          хэши обновятся в модели User.save().
        """
        user: User = super().save(commit=False)

        email = self.cleaned_data.get("email") or ""
        phone = self.cleaned_data.get("phone") or ""

        user.email_plain = email or ""
        user.phone_plain = phone or ""

        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """
    Редактирование профиля (email / телефон) в HTML.
    """

    email = forms.EmailField(
        label=_("Email"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "ps-input", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label=_("Телефон"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "ps-input",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "phone")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        user: User | None = kwargs.get("instance")
        if user is not None:
            initial = kwargs.setdefault("initial", {})
            initial.setdefault("email", user.email_plain)
            initial.setdefault("phone", user.phone_plain)
        super().__init__(*args, **kwargs)

    def clean_email(self) -> str:
        """
        Нормализуем email и проверяем уникальность (кроме текущего пользователя).
        """
        raw_email = self.cleaned_data.get("email")
        email = normalize_email(raw_email)
        if not email:
            return ""

        email_hash = hash_email(email)
        qs = User.objects.filter(email_hash=email_hash)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if email_hash and qs.exists():
            raise forms.ValidationError(
                _("Пользователь с таким email уже существует.")
            )
        return email

    def clean_phone(self) -> str:
        """
        Нормализуем телефон и проверяем уникальность (кроме текущего пользователя).
        """
        raw_phone = self.cleaned_data.get("phone") or ""
        if not raw_phone:
            return ""

        phone = normalize_phone(raw_phone)
        if not phone:
            raise forms.ValidationError(_("Некорректный формат телефона."))

        phone_hash = hash_phone(phone)
        qs = User.objects.filter(phone_hash=phone_hash)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if phone_hash and qs.exists():
            raise forms.ValidationError(
                _("Пользователь с таким телефоном уже существует.")
            )
        return phone

    def save(self, commit: bool = True) -> User:
        """
        Обновляем зашифрованные поля email/phone, хэши обновятся в модели.
        """
        user: User = super().save(commit=False)

        email = self.cleaned_data.get("email") or ""
        phone = self.cleaned_data.get("phone") or ""

        user.email_plain = email or ""
        user.phone_plain = phone or ""

        if commit:
            user.save()
        return user
