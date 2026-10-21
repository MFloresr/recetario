"""Pone foto a las recetas de la IA guardadas que no la tienen (por ejemplo, las anteriores a las fuentes nuevas)."""

from django.core.management.base import BaseCommand

from recipes.models import RecipeCache
from recipes.services.images import find_dish_image_or_fallback
from recipes.services.recipes import AI_SOURCE


class Command(BaseCommand):
    help = "Busca una foto de muestra para las recetas de la IA que no tienen. Con --dry-run no guarda nada."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="solo muestra qué foto se pondría")

    def handle(self, *args, dry_run=False, **options):
        sin_foto = RecipeCache.objects.filter(source=AI_SOURCE, image="")
        self.stdout.write(f"{sin_foto.count()} recetas de la IA sin foto")
        for receta in sin_foto:
            datos = receta.raw_data or {}
            foto = find_dish_image_or_fallback(receta.title, meal_type=datos.get("meal_type", ""))
            self.stdout.write(f"- {receta.title}: {foto['credit']}")
            if dry_run:
                continue
            receta.image = foto["url"]
            receta.raw_data = {**datos, "image_credit": foto["credit"], "image_page": foto["page"]}
            receta.save(update_fields=["image", "raw_data"])
