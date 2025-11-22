# accounts/forms.py

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from core.utils import normalize_phone
from .models import User


class LoginForm(AuthenticationForm):
    """
    Форма входа: одно поле для логина / email / телефона + пароль.
    """

    username = forms.CharField(
        label=_("Логин / Email / Телефон"),
        widget=forms.TextInput(attrs={"autofocus": True, "class": "ps-input"}),
    )

    def clean(self):
        """
        Подменяем username на реальный логин пользователя, чтобы
        AuthenticationForm могла вызвать authenticate() как обычно.
        """
        from .auth import find_user_by_identifier  # локальный импорт

        identifier = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if identifier and password:
            user = find_user_by_identifier(identifier)
            if user is not None:
                self.cleaned_data["username"] = user.get_username()

        return super().clean()


class RegisterForm(UserCreationForm):
    """
    Регистрация через HTML-форму.
    Email и телефон — опциональные, сохраняются в зашифрованном виде.
    """

    email = forms.EmailField(
        label=_("Email (опционально)"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "ps-input"}),
    )
    phone = forms.CharField(
        label=_("Телефон (опционально)"),
        required=False,
        widget=forms.TextInput(attrs={"class": "ps-input"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone")
        widgets = {
            "username": forms.TextInput(attrs={"class": "ps-input"}),
        }

    # В RegisterForm
    def clean_email(self) -> str:
        """
        Просто нормализуем email, без запросов к БД.
        """
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email

    def clean_phone(self) -> str:
        """
        Только нормализуем номер, без проверки уникальности.
        """
        phone = self.cleaned_data.get("phone") or ""
        if not phone:
            return ""

        phone = normalize_phone(phone)
        if not phone:
            raise forms.ValidationError(_("Некорректный формат телефона."))
        return phone

    def save(self, commit: bool = True) -> Any:
        user: User = super().save(commit=False)

        email = self.cleaned_data.get("email", "").strip().lower()
        phone = self.cleaned_data.get("phone", "")

        user.email_plain = email or ""
        user.phone_plain = normalize_phone(phone or "") if phone else ""

        if commit:
            user.save()
        return user

    def save(self, commit: bool = True) -> User:
        user: User = super().save(commit=False)
        email = self.cleaned_data.get("email") or ""
        phone = self.cleaned_data.get("phone") or ""
        if email:
            user.email_plain = email
        if phone:
            user.phone_plain = phone
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """
    Редактирование профиля (email/телефон).
    """

    email = forms.EmailField(
        label=_("Email"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "ps-input"}),
    )
    phone = forms.CharField(
        label=_("Телефон"),
        required=False,
        widget=forms.TextInput(attrs={"class": "ps-input"}),
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
        email = (self.cleaned_data.get("email") or "").strip().lower()
        # Больше НИКАКИХ запросов к User.objects.filter(email_encrypted=...)
        return email

    def clean_phone(self) -> str:
        phone = self.cleaned_data.get("phone") or ""
        if not phone:
            return ""

        phone = normalize_phone(phone)
        if not phone:
            raise forms.ValidationError(_("Некорректный формат телефона."))
        # Больше НИКАКИХ запросов к User.objects.filter(phone_encrypted=...)
        return phone

    def save(self, commit: bool = True) -> Any:
        user: User = super().save(commit=False)

        email = (self.cleaned_data.get("email") or "").strip().lower()
        phone = self.cleaned_data.get("phone") or ""

        user.email_plain = email or ""
        user.phone_plain = normalize_phone(phone or "") if phone else ""

        if commit:
            user.save()
        return user
