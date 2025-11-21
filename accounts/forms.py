# accounts/forms.py

from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from core.utils import normalize_phone
from .models import User


class RegisterForm(UserCreationForm):
    """
    Регистрация через HTML-форму.
    Email и телефон — опциональные, сохраняются в зашифрованном виде.
    """

    email = forms.EmailField(
        label=_("Email (опционально)"),
        required=False,
    )
    phone = forms.CharField(
        label=_("Телефон (опционально)"),
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone")

    def clean_phone(self) -> str:
        phone = self.cleaned_data.get("phone")
        if not phone:
            return ""
        return normalize_phone(phone)

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

    email = forms.EmailField(label=_("Email"), required=False)
    phone = forms.CharField(label=_("Телефон"), required=False)

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

    def clean_phone(self) -> str:
        phone = self.cleaned_data.get("phone")
        if not phone:
            return ""
        return normalize_phone(phone)

    def save(self, commit: bool = True) -> User:
        user: User = super().save(commit=False)
        email = self.cleaned_data.get("email") or ""
        phone = self.cleaned_data.get("phone") or ""
        user.email_plain = email
        user.phone_plain = phone
        if commit:
            user.save()
        return user
