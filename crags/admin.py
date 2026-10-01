from django.contrib import admin

from .models import Area, Crag, Photo


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Crag)
class CragAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "area",
        "family_rating",
        "stroller_friendly",
        "approach_minutes",
        "orientation",
    )

    list_filter = (
        "area",
        "family_rating",
        "stroller_friendly",
        "orientation",
    )

    search_fields = (
        "name",
        "area__name",
    )


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = (
        "crag",
        "caption",
        "created_at",
    )