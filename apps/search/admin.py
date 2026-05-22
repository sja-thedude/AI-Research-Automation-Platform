from django.contrib import admin

from .models import SearchQuery


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("text", "mode", "result_count", "duration_ms", "owner", "created_at")
    list_filter = ("mode",)
    search_fields = ("text",)
