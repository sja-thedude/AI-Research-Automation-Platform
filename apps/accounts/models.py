"""Identity, profiles and team-collaboration models.

Auth model is email-based (no username). Multi-tenancy is modeled with
Team + TeamMembership (role-based), which other apps scope resources to.
"""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, TimeStampedModel


class UserManager(BaseUserManager):
    """Email-based manager (username field removed)."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=is_superuser=True")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Custom user keyed by email. UUID PK keeps IDs opaque in tokens/URLs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email


class Profile(TimeStampedModel):
    """1:1 user profile holding non-auth attributes & AI preferences."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    organization = models.CharField(max_length=160, blank=True)
    # Per-user AI defaults (override platform defaults at request time).
    preferred_model = models.CharField(max_length=64, blank=True)
    ai_preferences = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"


class Team(BaseModel):
    """A collaboration workspace. Resources across apps can be team-scoped."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_teams"
    )
    members = models.ManyToManyField(
        User,
        through="TeamMembership",
        through_fields=("team", "user"),  # disambiguate from invited_by FK
        related_name="teams",
    )
    settings = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.name


class TeamMembership(TimeStampedModel):
    """Role-based membership linking users to teams."""

    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        EDITOR = "editor", _("Editor")
        VIEWER = "viewer", _("Viewer")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="memberships"
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.VIEWER
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invites",
    )

    class Meta:
        unique_together = ("user", "team")
        indexes = [models.Index(fields=["team", "role"])]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.team.name} ({self.role})"
