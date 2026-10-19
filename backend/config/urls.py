"""Rutas del proyecto. La API vive bajo /api/ y cada app añade sus propias rutas."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("recipes.urls")),
]
