"""Seed a demo user + team for local exploration.

    python manage.py seed_demo
    # -> demo@neuraforge.ai / demo12345
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a demo user, team and a sample note."

    def handle(self, *args, **opts):
        from apps.accounts.models import Team, TeamMembership, User
        from apps.notes.models import Note

        user, created = User.objects.get_or_create(
            email="demo@neuraforge.ai",
            defaults={"full_name": "Demo User", "is_verified": True},
        )
        if created:
            user.set_password("demo12345")
            user.save()

        team, _ = Team.objects.get_or_create(
            slug="demo-team", defaults={"name": "Demo Team", "owner": user}
        )
        TeamMembership.objects.get_or_create(
            user=user, team=team, defaults={"role": TeamMembership.Role.ADMIN}
        )
        Note.objects.get_or_create(
            owner=user,
            title="Welcome to NeuraForge AI",
            defaults={"content": "Upload a document, then ask the chat about it."},
        )

        self.stdout.write(
            self.style.SUCCESS("Seeded demo@neuraforge.ai / demo12345 (+ Demo Team)")
        )
