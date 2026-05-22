from django.contrib import admin

from .models import Note, NoteLink, Tag


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_pinned", "updated_at")
    list_filter = ("is_pinned", "tags")
    search_fields = ("title", "content")
    filter_horizontal = ("tags",)


admin.site.register(Tag)
admin.site.register(NoteLink)
