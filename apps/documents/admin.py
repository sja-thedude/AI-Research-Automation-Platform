from django.contrib import admin

from .models import Document, Folder


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "status", "owner", "word_count", "created_at")
    list_filter = ("file_type", "status", "created_at")
    search_fields = ("title", "content_hash")
    readonly_fields = ("content_hash", "extracted_text", "metadata", "created_at", "updated_at")
    raw_id_fields = ("owner", "team", "folder")


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "parent", "created_at")
    search_fields = ("name",)
