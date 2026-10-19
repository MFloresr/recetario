"""Rutas del proyecto. La API vive bajo /api/ y cada app añade sus propias rutas."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("recipes.urls")),
]
