from django.core.management import call_command

from recipes.models import RecipeCache
from recipes.services.images import FOTOS_RESPALDO


def receta(external_id, title, image="", source="ai", meal_type="postre"):
    return RecipeCache.objects.create(external_id=external_id, source=source, title=title, image=image, raw_data={"meal_type": meal_type, "tips": []})


def test_pone_foto_a_las_recetas_de_la_ia_sin_ella(db, wikipedia):
    sin = receta("ai-1-a", "Plato inventado")
    con = receta("ai-1-b", "Otro", image="https://img/ya.jpg")
    ajena = receta("123", "De TheMealDB", source="themealdb")
    call_command("completar_fotos")
    for r in (sin, con, ajena):
        r.refresh_from_db()
    assert sin.image == FOTOS_RESPALDO["postre"]["url"]
    assert sin.raw_data["image_credit"] == FOTOS_RESPALDO["postre"]["credit"] and sin.raw_data["meal_type"] == "postre"
    assert con.image == "https://img/ya.jpg"
    assert ajena.image == ""


def test_dry_run_no_guarda_nada(db, wikipedia):
    sin = receta("ai-1-a", "Plato inventado")
    call_command("completar_fotos", "--dry-run")
    sin.refresh_from_db()
    assert sin.image == ""
