"""Carga el catálogo de platos desde Wikidata y TheMealDB. Se puede repetir: actualiza sin duplicar."""

from django.core.management.base import BaseCommand

from recipes.models import Dish
from recipes.services import catalog_import as ci

CAMPOS = ["name_es", "name_en", "description", "country", "meal_type", "ingredients", "steps", "image", "image_credit", "image_license"]


class Command(BaseCommand):
    help = "Carga platos en el catálogo. Con --dry-run solo cuenta, sin guardar."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--fuente", choices=["wikidata", "themealdb", "todas"], default="todas")
        parser.add_argument("--paises", help="códigos ISO separados por comas (por defecto, catalog_import.PAISES)")

    def guardar(self, platos, dry_run):
        nuevos = 0
        for plato in platos:
            existente = Dish.objects.filter(source=plato["source"], source_id=plato["source_id"]).first()
            if existente is None:
                nuevos += 1
                if not dry_run:
                    Dish.objects.create(**plato)
            elif not dry_run:
                # no pisar lo ya revisado o completado: solo rellenar huecos
                for campo in CAMPOS:
                    if plato.get(campo) and not getattr(existente, campo):
                        setattr(existente, campo, plato[campo])
                existente.save()
        return nuevos

    def handle(self, *args, dry_run=False, fuente="todas", paises=None, **options):
        if fuente in ("wikidata", "todas"):
            for iso in paises.split(",") if paises else ci.PAISES:
                try:
                    platos = ci.platos_wikidata(iso.strip().upper())
                except Exception as exc:  # un país que falla no debe parar la carga
                    self.stderr.write(f"{iso}: error de Wikidata ({exc})")
                    continue
                self.stdout.write(f"wikidata {iso}: {len(platos)} platos, {self.guardar(platos, dry_run)} nuevos")
        if fuente in ("themealdb", "todas"):
            ya = set(Dish.objects.filter(source="themealdb").values_list("source_id", flat=True))
            platos = ci.platos_themealdb(ya_cargados=ya)
            self.stdout.write(f"themealdb: {len(platos)} platos, {self.guardar(platos, dry_run)} nuevos")
