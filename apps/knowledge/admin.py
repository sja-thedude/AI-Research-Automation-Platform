from django.contrib import admin

from .models import Entity, Relationship


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "owner", "created_at")
    list_filter = ("kind",)
    search_fields = ("name",)


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = ("subject", "predicate", "obj", "weight", "owner")
    search_fields = ("predicate",)
