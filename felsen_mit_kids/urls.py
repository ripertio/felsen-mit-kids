from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path


def home(request):
    return render(request, "home.html")


def docs(request):
    return render(request, "docs.html")


urlpatterns = [
    path("", home, name="home"),
    path("crags/", include("crags.urls")),
    path("docs/", docs, name="docs"),
    path("admin/", admin.site.urls),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )