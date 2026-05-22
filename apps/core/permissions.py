"""Reusable DRF object-level permissions for multi-tenant resources."""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Allow access only to the object's owner."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "owner_id", None) == request.user.id


class IsOwnerOrTeamMember(permissions.BasePermission):
    """Allow the owner, or any member of the object's team.

    Read-only access is granted to team members; writes require ownership
    unless the member holds an elevated team role.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(obj, "owner_id", None) == user.id:
            return True
        team_id = getattr(obj, "team_id", None)
        if not team_id:
            return False
        membership = user.memberships.filter(team_id=team_id).first()
        if not membership:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return membership.role in {"admin", "editor"}


class IsTeamAdmin(permissions.BasePermission):
    """Object-level: caller must be an admin of the object's team."""

    def has_object_permission(self, request, view, obj):
        team_id = getattr(obj, "team_id", None) or getattr(obj, "id", None)
        return request.user.memberships.filter(
            team_id=team_id, role="admin"
        ).exists()
