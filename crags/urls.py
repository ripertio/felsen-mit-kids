from django.urls import path

from . import views

app_name = "crags"

urlpatterns = [
    path("", views.crag_list, name="list"),
    path("<int:pk>/", views.crag_detail, name="detail"),
]