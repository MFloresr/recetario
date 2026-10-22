"""La IA completa los platos del catálogo (nombre en español, tipo, calorías, dietas, receta). Quedan sin revisar."""

from django.core.management.base import BaseCommand

from recipes.models import Dish
from recipes.services.ai import get_ai_service

LOTE = 5


class Command(BaseCommand):
    help = "Completa con la IA los platos sin enriquecer. Se puede repetir: sigue donde lo dejó."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=50, help="máximo de platos en esta pasada")
        parser.add_argument("--pais", help="solo los de un país (ISO)")
        parser.add_argument("--dry-run", action="store_true", help="muestra el resultado sin guardar")

    def handle(self, *args, limite=50, pais=None, dry_run=False, **options):
        pendientes = Dish.objects.filter(enriched=False)
        if pais:
            pendientes = pendientes.filter(country=pais.upper())
        ids = list(pendientes.order_by("id").values_list("id", flat=True)[:limite])
        self.stdout.write(f"{len(ids)} platos por completar")
        ia = get_ai_service()
        for i in range(0, len(ids), LOTE):
            platos = list(Dish.objects.filter(id__in=ids[i:i + LOTE]).order_by("id"))
            entrada = [
                {"name": p.name_en or p.name_es, "country": p.country, "ingredients": p.ingredients, "steps": p.steps[:1500]}
                for p in platos
            ]
            try:
                salida = ia.enrich_dishes(entrada)
            except Exception as exc:  # un lote que falla no debe parar el resto
                self.stderr.write(f"lote {i // LOTE + 1}: {exc}")
                continue
            for plato, datos in zip(platos, salida):
                self.stdout.write(f"- {plato.name_es} → {datos['name_es']} {datos['diets']} {datos['calories']} kcal")
                if dry_run:
                    continue
                plato.name_es = datos["name_es"]
                plato.description = plato.description or datos["description"][:400]
                plato.meal_type = plato.meal_type or datos["meal_type"]
                plato.diets = datos["diets"]
                plato.calories = datos["calories"]
                if datos["ingredients"]:
                    plato.ingredients = [{"ingredient": x["name"], "measure": x["quantity"]} for x in datos["ingredients"]]
                if datos["steps"]:
                    plato.steps = "\n".join(datos["steps"])
                plato.enriched = True  # reviewed sigue en False: son datos generados
                plato.save()
