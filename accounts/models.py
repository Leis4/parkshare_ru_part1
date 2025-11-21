# accounts/models.py

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_cryptography.fields import encrypt


class User(AbstractUser):
    """
    Кастомный пользователь:
    - UUID как первичный ключ;
    - роль (driver / owner / admin);
    - email/телефон в зашифрованном виде (django-cryptography-django5).
    """

    class Role(models.TextChoices):
        DRIVER = "driver", _("Водитель")
        OWNER = "owner", _("Владелец парковки")
        ADMIN = "admin", _("Администратор")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    role = models.CharField(
        _("Роль"),
        max_length=16,
        choices=Role.choices,
        default=Role.DRIVER,
        help_text=_("Определяет права доступа в системе."),
    )

    email_encrypted = encrypt(
        models.EmailField(
            _("Email (зашифрованный)"),
            blank=True,
            null=True,
            help_text=_("Опциональный email, хранится в зашифрованном виде."),
        )
    )

    phone_encrypted = encrypt(
        models.CharField(
            _("Телефон (зашифрованный)"),
            max_length=32,
            blank=True,
            null=True,
            help_text=_("Опциональный телефон, хранится в зашифрованном виде."),
        )
    )

    owner_request_pending = models.BooleanField(
        _("Запрошено повышение до владельца"),
        default=False,
        help_text=_("Пользователь подал заявку на роль владельца парковки."),
    )

    # username + password остаются стандартными полями AbstractUser
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self) -> str:
        return self.username

    # Удобные свойства для расшифрованных контактов

    @property
    def email_plain(self) -> str:
        """
        Удобное свойство для доступа к расшифрованному email.
        В коде (и в админке) можно использовать user.email_plain.
        """
        return self.email_encrypted or ""

    @email_plain.setter
    def email_plain(self, value: str) -> None:
        self.email_encrypted = value

    @property
    def phone_plain(self) -> str:
        return self.phone_encrypted or ""

    @phone_plain.setter
    def phone_plain(self, value: str) -> None:
        self.phone_encrypted = value

    @property
    def is_driver(self) -> bool:
        return self.role == self.Role.DRIVER

    @property
    def is_owner(self) -> bool:
        return self.role in (self.Role.OWNER, self.Role.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser
