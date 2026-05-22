from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsTeamAdmin

from .models import Team, TeamMembership
from .serializers import (
    EmailTokenObtainPairSerializer,
    ProfileSerializer,
    RegisterSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /auth/register — open self-service signup."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    """POST /auth/login — returns access+refresh JWT and the user payload."""

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/me — current user."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/profile — current user's profile + AI preferences."""

    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class TeamViewSet(viewsets.ModelViewSet):
    """CRUD for teams the caller belongs to, plus member management."""

    serializer_class = TeamSerializer

    def get_queryset(self):
        return (
            Team.objects.filter(memberships__user=self.request.user)
            .distinct()
            .prefetch_related("memberships")
        )

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        team = serializer.save(
            owner=self.request.user,
            slug=self._unique_slug(name),
        )
        # Creator becomes the first admin.
        TeamMembership.objects.create(
            user=self.request.user, team=team, role=TeamMembership.Role.ADMIN
        )

    @staticmethod
    def _unique_slug(name: str) -> str:
        base = slugify(name) or "team"
        slug, i = base, 1
        while Team.objects.filter(slug=slug).exists():
            i += 1
            slug = f"{base}-{i}"
        return slug

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        """GET list members / POST invite a member by email (admins only)."""
        team = self.get_object()
        if request.method == "GET":
            qs = team.memberships.select_related("user")
            return Response(TeamMembershipSerializer(qs, many=True).data)

        if not team.memberships.filter(
            user=request.user, role=TeamMembership.Role.ADMIN
        ).exists():
            return Response({"detail": "Admins only."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TeamMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(team=team, invited_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="members/(?P<membership_id>[^/.]+)",
        permission_classes=[permissions.IsAuthenticated, IsTeamAdmin],
    )
    def remove_member(self, request, pk=None, membership_id=None):
        team = self.get_object()
        deleted, _ = team.memberships.filter(id=membership_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
